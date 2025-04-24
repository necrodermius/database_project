import os

from django.db import models, transaction
from datetime import time, date, timedelta
from collections import defaultdict
import logging
import random
import django

# Налаштування Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")  # Вкажіть свій файл налаштувань
django.setup()

# Імпорт моделей
from database.models import StudyPlan, Course, Teacher, Group, Subgroup, Lesson

logger = logging.getLogger(__name__)


class ScheduleGenerator:
    LECTURE_TIMESLOTS = [
        (time(9, 0), time(10, 20)),
        (time(10, 30), time(11, 50)),
        (time(12, 10), time(13, 30)),
        (time(13, 40), time(15, 0)),
        (time(15, 10), time(16, 30)),
        (time(16, 40), time(18, 0)),
        (time(18, 10), time(19, 30)),
    ]

    WORK_DAYS = [0, 1, 2, 3, 4]  # Пн-Пт
    LECTURE_DAYS = []
    PRACTICE_DAYS = []

    MAX_LESSONS_FOR_SUBGROUP = 4
    MAX_LESSONS_FOR_TEACHER = 7 # поки не актуально

    def __init__(self, study_plan, semester, start_date, end_date):
        self.LECTURE_DAYS = random.sample(self.WORK_DAYS, 2)
        self.PRACTICE_DAYS = [day for day in self.WORK_DAYS if day not in self.LECTURE_DAYS]

        self.study_plan = study_plan
        self.semester = semester
        self.start_date = start_date
        self.end_date = end_date

        # Перевірка вхідних даних
        self._validate_input()

        self.groups = Group.objects.filter(study_plan=study_plan).prefetch_related('subgroups')
        self.courses = Course.objects.filter(
            study_plan=study_plan,
            semester=semester
        ).select_related('teacher')
        self.subgroups = Subgroup.objects.filter(group__in=self.groups)

        logger.info(f"Initialized with {self.groups.count()} groups, "
                    f"{self.courses.count()} courses, "
                    f"{self.subgroups.count()} subgroups")

        # Кешування даних
        self.teacher_workload = defaultdict(int)
        self.group_schedule = defaultdict(list)
        self.subgroup_schedule = defaultdict(list)

    def _validate_input(self):
        """Перевірка коректності вхідних параметрів"""
        if not self.study_plan:
            raise ValueError("Study plan is required")

        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")

        logger.info(f"Generating schedule for {self.study_plan.name} "
                    f"(semester {self.semester}) "
                    f"from {self.start_date} to {self.end_date}")

    def generate_schedule(self):
        """Основна функція генерації розкладу"""
        try:
            with transaction.atomic():  # Вся транзакція відбувається в цьому блоку
                self._generate_lectures()
                self._generate_practices()
                logger.info("Schedule generated successfully")
                return self._get_final_schedule()
        except Exception as e:
            logger.error(f"Schedule generation failed: {str(e)}")
            # Автоматичний rollback відбувається при виході з блоку
            raise

    def _generate_lectures(self):
        current_date = self.start_date
        lecture_courses = [c for c in self.courses if c.lecture_hours > 0]

        lectures_needed = {
            c.id: c.lecture_hours // 2 for c in lecture_courses
        }

        lectures_created = defaultdict(int)

        while current_date <= self.end_date:
            if current_date.weekday() not in self.LECTURE_DAYS:
                current_date += timedelta(days=1)
                continue

            for start_time, end_time in self.LECTURE_TIMESLOTS:
                random.shuffle(lecture_courses)  # рандомізуємо порядок для рівномірності
                for course in lecture_courses:
                    if lectures_created[course.id] >= lectures_needed[course.id]:
                        continue

                    if not self._is_teacher_available(course.teacher, current_date, start_time, end_time):
                        continue

                    # daily_teacher_lessons = Lesson.objects.filter(
                    #     course__teacher=course.teacher, date=current_date
                    # ).count()
                    #
                    # if daily_teacher_lessons >= 4:  # обмеження 4 заняття на день
                    #     continue

                    subgroups_to_create = []
                    for subgroup in self.subgroups:
                        daily_subgroup_lessons = Lesson.objects.filter(
                            subgroup=subgroup, date=current_date
                        ).count()

                        if daily_subgroup_lessons < self.MAX_LESSONS_FOR_SUBGROUP:
                            subgroups_to_create.append(subgroup)

                    if not subgroups_to_create:
                        continue

                    lessons = [
                        Lesson(
                            course=course,
                            subgroup=subgroup,
                            date=current_date,
                            start_time=start_time,
                            lesson_type='Lecture'
                        ) for subgroup in subgroups_to_create
                    ]

                    Lesson.objects.bulk_create(lessons)
                    lectures_created[course.id] += 1
                    break  # один курс на таймслот

            current_date += timedelta(days=1)

    def _generate_practices(self):
        current_date = self.start_date
        practice_courses = [c for c in self.courses if c.practice_hours > 0]

        # Визначаємо кількість занять, які треба провести для кожної підгрупи
        practices_needed = {
            (course.id, subgroup.id): course.practice_hours // 2
            for course in practice_courses
            for subgroup in self.subgroups
            if subgroup.group.study_plan == course.study_plan
        }

        # Створюємо лічильник занять
        practices_created = defaultdict(int)

        while current_date <= self.end_date:
            if current_date.weekday() not in self.PRACTICE_DAYS:
                current_date += timedelta(days=1)
                continue
            logger.info(f"Оброблюється {current_date} день")
            for start_time, end_time in self.LECTURE_TIMESLOTS:
                random.shuffle(practice_courses)  # Для рівномірного розподілу

                for course in practice_courses:
                    for subgroup in self.subgroups.filter(group__study_plan=course.study_plan):

                        # Перевірка чи достатньо занять вже створено для цієї підгрупи та курсу
                        key = (course.id, subgroup.id)
                        if practices_created[key] >= practices_needed[key]:
                            continue

                        if self._has_lesson_at(subgroup, current_date, start_time):
                            continue

                        if not self._is_teacher_available(course.teacher, current_date, start_time, end_time):
                            continue

                        # daily_teacher_lessons = Lesson.objects.filter(
                        #     course__teacher=course.teacher, date=current_date
                        # ).count()
                        #
                        # if daily_teacher_lessons >= 5:
                        #     continue

                        daily_subgroup_lessons = Lesson.objects.filter(
                            subgroup=subgroup, date=current_date
                        ).count()

                        if daily_subgroup_lessons >= self.MAX_LESSONS_FOR_SUBGROUP:
                            continue

                        Lesson.objects.create(
                            course=course,
                            subgroup=subgroup,
                            date=current_date,
                            start_time=start_time,
                            lesson_type='Practice'
                        )

                        practices_created[key] += 1
                        self.teacher_workload[course.teacher] += 1

            current_date += timedelta(days=1)

    def _is_teacher_available(self, teacher, date, start_time, end_time):
        """Перевірка доступності викладача з дебаг-логом"""
        existing_lessons = Lesson.objects.filter(
            course__teacher=teacher,
            date=date,
            start_time=start_time
        ).exists()

        # teacher_courses = Course.objects.filter(teacher=teacher, semester=self.semester)
        # total_hours = sum(c.lecture_hours + c.practice_hours for c in teacher_courses)

        # logger.debug(
        #     f"Teacher {teacher} availability check: "
        #     f"Existing lessons: {existing_lessons}, "
        #     f"Workload: {self.teacher_workload[teacher]}/{total_hours}, "
        #     f"Allowed hours: {teacher.allowed_hours}"
        # )

        return (
                not existing_lessons
                # and self.teacher_workload[teacher] < total_hours
                # and self.teacher_workload[teacher] < teacher.allowed_hours
        )

    def _has_lesson_at(self, subgroup, date, start_time):
        """Перевірка наявності занять з кешуванням"""
        return Lesson.objects.filter(
            subgroup=subgroup,
            date=date,
            start_time=start_time
        ).exists()

    def _get_final_schedule(self):
        """Формування підсумкового розкладу"""
        lessons = Lesson.objects.filter(
            date__range=(self.start_date, self.end_date),
            subgroup__in=self.subgroups
        ).select_related('course', 'subgroup').order_by('date', 'start_time')

        schedule = defaultdict(lambda: defaultdict(list))
        for lesson in lessons:
            schedule[lesson.subgroup][lesson.date].append(lesson)

        logger.info(f"Final schedule contains {lessons.count()} lessons")
        return schedule
# Приклад використання


if __name__ == "__main__":
    study_plans = StudyPlan.objects.all()
    Lesson.objects.all().delete()
    for sp in study_plans:
        #for i in range(32, 38):
        study_plan = StudyPlan.objects.get(pk=sp.id)  # Отримуємо навчальний план
        semester = 2
        start_date = date(2025, 1, 20)  # Початок семестру
        end_date = date(2025, 5, 31)  # Кінець семестру

    generator = ScheduleGenerator(study_plan, semester, start_date, end_date)
    schedule = generator.generate_schedule()
