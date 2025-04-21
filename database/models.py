from django.db import models

class StudyPlan(models.Model):
    name = models.CharField(max_length=255)
    year_of_effect = models.PositiveIntegerField()
    number_of_semesters = models.PositiveSmallIntegerField()
    approval_date = models.DateField()
    plan_author = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Teacher(models.Model):
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=50)  # e.g., Assistant, Associate Professor, Professor
    allowed_hours = models.PositiveIntegerField()
    rate = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return self.full_name

class Course(models.Model):
    study_plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.CASCADE,
        related_name='courses'
    )
    course_name = models.CharField(max_length=255)
    lecture_hours = models.PositiveIntegerField()
    practice_hours = models.PositiveIntegerField()
    semester = models.PositiveSmallIntegerField()
    credits = models.PositiveIntegerField()
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='teachers'
    )
    def __str__(self):
        return self.course_name

class Group(models.Model):
    name = models.CharField(max_length=255)
    major = models.CharField(max_length=255)
    year = models.PositiveSmallIntegerField()
    start_year = models.PositiveIntegerField()
    study_plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.CASCADE,
        related_name='groups'
    )

    def __str__(self):
        return self.name

class Subgroup(models.Model):
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='subgroups'
    )
    number = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.group.name} / {self.number} "

class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    subgroup = models.ForeignKey(
        Subgroup,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    date = models.DateField()
    start_time = models.TimeField()
    lesson_type = models.CharField(max_length=50)  # Lecture, Practice, Lab, etc.

    def __str__(self):
        return f"{self.course.course_name} ({self.lesson_type})"
