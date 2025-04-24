#!/usr/bin/env python
import os
import django

# 1) Встановлюємо налаштування Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")  # замініть на шлях до ваших налаштувань
django.setup()

# 2) Імпортуємо моделі
from database.models import Subgroup, Lesson
from django.db.models import Count, Q

def main():
    # 3) Анотуємо кожну підгрупу двома лічильниками: lectures і practices
    subgroups = Subgroup.objects.annotate(
        lectures=Count('lessons', filter=Q(lessons__lesson_type='Lecture')),
        practices=Count('lessons', filter=Q(lessons__lesson_type='Practice')),
    ).order_by('group__name', 'number')

    # 4) Виводимо результат
    print(f"{'Підгрупа':<20} {'Лекцій':>8} {'Практик':>8}")
    print("-" * 38)
    for sg in subgroups:
        name = f"{sg.group.name}/{sg.number}"
        print(f"{name:<20} {sg.lectures:>8} {sg.practices:>8}")

if __name__ == "__main__":
    main()
