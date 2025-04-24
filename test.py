import os
import django
from django.db import transaction
from faker import Faker
import random
from datetime import date, time, timedelta
# Замініть 'project.settings' на шлях до вашого файлу налаштувань
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()
from database.models import StudyPlan, Teacher, Course, Group, Subgroup, Lesson



fake = Faker("uk_UA")  # Якщо хочете українські дані. Можна змінити на "en_US" чи інші локалі.

# Набори випадкових даних для позицій та типів занять
POSITIONS = ["Assistant", "Associate Professor", "Professor", "Senior Lecturer"]
LESSON_TYPES = ["Lecture", "Practice", "Lab", "Seminar"]

COUNT_OF_STUDY_PLANS = 1
COUNT_OF_GROUPS_BY_YEAR = 5
COUNT_OF_SUBGROUPS_BY_GROUP = 2
COUNT_OF_COURSES_BY_SEMESTER = 6
COUNT_OF_TEACHER_COURSES = 2
STUDY_PLAN_DURATION = 2 # семестрів
LECTURE_HOURS = 20*2
PRACTICE_HOURS = 20*2

@transaction.atomic
def generate_test_data():
    """
    Генерує великий обсяг випадкових тестових даних для всіх моделей:
    - StudyPlan (навчальні плани)
    - Teacher (викладачі)
    - Course (курси)
    - Group (групи)
    - Subgroup (підгрупи)
    - Lesson (заняття)

    Заняття генеруються з майбутніми датами (від сьогодні до 90 днів вперед),
    щоб імітувати реальний розклад.
    """


    Lesson.objects.all().delete()
    Subgroup.objects.all().delete()
    Group.objects.all().delete()
    Course.objects.all().delete()
    Teacher.objects.all().delete()
    StudyPlan.objects.all().delete()

    # 1. Створимо кілька навчальних планів (StudyPlan)
    study_plans = []
    for year in range(2021, 2021 + COUNT_OF_STUDY_PLANS):  # 2020...2025
        sp = StudyPlan.objects.create(
            name=f"Навчальний план {year}",
            year_of_effect=year,
            number_of_semesters=STUDY_PLAN_DURATION,  # можна змінити, якщо потрібно
            approval_date=fake.date_between_dates(
                date_start=date(year, 1, 1),
                date_end=date(year, 12, 31)
            ),
            plan_author=fake.name()
        )
        study_plans.append(sp)

    # 2. Створимо викладачів (Teacher)
    teachers = []
    for _ in range(int(COUNT_OF_COURSES_BY_SEMESTER / COUNT_OF_STUDY_PLANS * COUNT_OF_STUDY_PLANS / STUDY_PLAN_DURATION)):  # 20 викладачів ///////////////////////
        t = Teacher.objects.create(
            full_name=fake.name(),
            position=random.choice(POSITIONS),
            allowed_hours=1000, #random.randint(300, 600),
            rate=round(random.uniform(0.5, 1.0), 2)
        )
        teachers.append(t)

    # 3. Створимо групи (Group) для кожного навчального плану
    current_year = date.today().year

    # Припустимо, у вас вже є список навчальних планів (study_plans)
    groups = []
    for sp in study_plans:
        # Обчислюємо поточний курс на основі року початку навчання
        course_year = current_year - sp.year_of_effect + 1
        # Створимо, наприклад, 4 групи для кожного плану
        for i in range(1, COUNT_OF_GROUPS_BY_YEAR + 1):    # ////////////////////////////
            g = Group.objects.create(
                name=f"{sp.year_of_effect}-Група-{i}",
                major=fake.job(),  # або можна вказати конкретну спеціальність
                year=course_year,  # обчислене значення
                start_year=sp.year_of_effect,
                study_plan=sp
            )
            groups.append(g)

    # 4. Створимо підгрупи (Subgroup) у кожній групі
    subgroups = []
    for g in groups:
        # Наприклад, дві підгрупи у кожній групі
        for sub_number in range(1, COUNT_OF_SUBGROUPS_BY_GROUP + 1):                   # ///////////////////////////////
            sg = Subgroup.objects.create(
                group=g,
                number=sub_number
            )
            subgroups.append(sg)

    # 5. Створимо курси (Course)
    course_names = [
        "Математика", "Програмування", "Фізика", "Хімія", "Лінійна алгебра",
        "Дискретна математика", "Бази даних", "Операційні системи",
        "Комп'ютерні мережі", "Теорія ймовірностей", "Чисельні методи",
        "Англійська мова", "Економіка", "Педагогіка", "Філософія"
    ]
    courses = []
    for i in range(COUNT_OF_COURSES_BY_SEMESTER):  # 50 випадкових курсів ///////////////////////////
        sp = random.choice(study_plans)
        t = teachers[i // COUNT_OF_TEACHER_COURSES]
        c_name = random.choice(course_names)
        c = Course.objects.create(
            study_plan=sp,
            course_name=c_name,
            lecture_hours=LECTURE_HOURS,
            practice_hours=PRACTICE_HOURS,
            semester=2,
            credits=random.randint(3, 6),
            teacher=t
        )
        courses.append(c)

    # # 6. Створимо заняття (Lesson) для кожного курсу
    # # Генеруємо дати від сьогодні до 90 днів у майбутньому, щоб не було занять у минулому.
    # today = date.today()
    # future_date_end = today + timedelta(days=90)
    #
    # for c in courses:
    #     # Знаходимо всі підгрупи, що належать групам з даного навчального плану курсу
    #     relevant_groups = Group.objects.filter(study_plan=c.study_plan)
    #     relevant_subgroups = Subgroup.objects.filter(group__in=relevant_groups)
    #
    #     # Для кожної підгрупи генеруємо від 20 до 50 занять для цього курсу
    #     for sg in relevant_subgroups:
    #         for _ in range(random.randint(20, 50)):
    #             random_date = fake.date_between_dates(date_start=today, date_end=future_date_end)
    #             random_time = time(
    #                 hour=random.randint(8, 18),
    #                 minute=random.choice([0, 15, 30, 45])
    #             )
    #             Lesson.objects.create(
    #                 course=c,
    #                 subgroup=sg,
    #                 date=random_date,
    #                 start_time=random_time,
    #                 lesson_type=random.choice(LESSON_TYPES)
    #             )
    print("Багато тестових даних успішно створено!")


# Виклик функції для генерації даних, якщо запускаєте цей скрипт напряму:
if __name__ == "__main__":
    generate_test_data()