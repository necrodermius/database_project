from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

from database.models import Lesson, Subgroup


# Create your views here.

def home(request):
    if not request.user.is_authenticated:
        return redirect('login')  # Перенаправление на страницу входа, если пользователь не залогинен
    return render(request, 'database/home.html')



def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Якщо користувач має статус адміністратора, перекидаємо його до адмінки
            if user.is_staff:
                return redirect('/admin/')
            # Якщо це студент – перенаправляємо на головну сторінку додатку
            else:
                return redirect('schedule')
        else:
            messages.error(request, "Невірне ім'я користувача або пароль.")
    return render(request, 'database/login.html')

def logout_view(request):
    logout(request)
    return  render(request, 'database/login.html')

import datetime

@login_required(login_url='login')
def dashboard(request):
    # 1) Зчитуємо параметри
    subgroup_id = request.GET.get('subgroup')
    date_str    = request.GET.get('date')

    # 2) За замовчуванням — lessons=None
    lessons = None

    # 3) Якщо є subgroup — обов’язково повертаємо QuerySet (можливо порожній)
    if subgroup_id:
        # Парсимо дату, або беремо сьогодні
        if date_str:
            try:
                parsed_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                parsed_date = datetime.date.today()
        else:
            parsed_date = datetime.date.today()

        # Формуємо QuerySet (може бути порожнім)
        lessons = (
            Lesson.objects
                  .filter(subgroup__id=subgroup_id, date=parsed_date)
                  .order_by('course__course_name')
                  .distinct('course__course_name')[:10]
        )

    # 4) Завжди передаємо підгрупи для селектора
    subgroups = Subgroup.objects.all()

    # 5) Контекст
    return render(request, 'database/dashboard.html', {
        'user':      request.user,
        'lessons':   lessons,
        'subgroups': subgroups,
    })

from django.core.paginator import Paginator
from collections import defaultdict
from itertools import cycle
def schedule_view(request):
    lessons_qs = (
        Lesson.objects
        .select_related('course', 'course__teacher', 'subgroup', 'subgroup__group')
        .order_by('date', 'start_time')
    )

    # розбиття на тижні (як раніше)
    if lessons_qs.exists():
        first_date = lessons_qs.first().date
        last_date  = lessons_qs.last().date
        first_monday = first_date - datetime.timedelta(days=first_date.weekday())
        last_monday  = last_date  - datetime.timedelta(days=last_date.weekday())
        total_weeks = ((last_monday - first_monday).days // 7) + 1
        week_starts = [ first_monday + datetime.timedelta(weeks=i) for i in range(total_weeks) ]
    else:
        week_starts = []

    paginator   = Paginator(week_starts, 1)
    page_number = request.GET.get('page') or 1
    page_obj    = paginator.get_page(page_number)

    if page_obj.object_list:
        start_week = page_obj.object_list[0]
        end_week   = start_week + datetime.timedelta(days=6)
        lessons    = lessons_qs.filter(date__range=(start_week, end_week))
    else:
        start_week = end_week = None
        lessons    = Lesson.objects.none()

    # дні тижня
    days = [ start_week + datetime.timedelta(days=i) for i in range(7) ] if start_week else []

    # унікальні timeslots
    timeslots = sorted({ l.start_time for l in lessons })

    # групи + підгрупи
    subgroups_qs = (
        Subgroup.objects
        .filter(lessons__in=lessons)
        .select_related('group')
        .order_by('group__name', 'number')
        .distinct()
    )
    group_map = defaultdict(list)
    for sg in subgroups_qs:
        group_map[sg.group].append(sg)
    groups = [ {'group': g, 'subgroups': group_map[g]} for g in sorted(group_map.keys(), key=lambda x: x.name) ]

    # створюємо lesson_map[дата][час][subgroup_id] = lesson
    lesson_map = {}
    for l in lessons:
        lesson_map.setdefault(l.date, {}).setdefault(l.start_time, {})[l.subgroup.id] = l

    # збираємо рядки
    rows = []
    for day in days:
        for idx, time in enumerate(timeslots):
            cells = []
            for grp in groups:
                for sg in grp['subgroups']:
                    cells.append( lesson_map.get(day, {}).get(time, {}).get(sg.id) )
            rows.append({
                'day':     day,
                'time':    time,
                'is_first': idx == 0,
                'rowspan': len(timeslots),
                'cells':   cells,
            })

    # ————— тепер мапа курсів на кольори —————
    # беремо унікальні курси в цьому тижні
    seen = set()
    unique_courses = []
    for l in lessons:
        cid = l.course.id
        if cid not in seen:
            seen.add(cid)
            unique_courses.append(l.course)

    seen_teachers = set()
    unique_teachers = []
    for l in lessons:
        tid = l.course.teacher.id
        if tid not in seen_teachers:
            seen_teachers.add(tid)
            unique_teachers.append(l.course.teacher)

    # палітра і цикл
    palette = ['#e57373', '#81c784', '#64b5f6', '#fff176', '#ba68c8', '#4db6ac', '#ffb74d', '#a1887f', '#90a4ae',
               '#aed581']
    color_cycle = cycle(palette)

    # мапимо ID викладача на колір
    teacher_colors = {teacher.id: next(color_cycle) for teacher in unique_teachers}

    # мапа курсів на колір викладача (щоб використовувати в шаблоні як course_colors[course.id])
    course_colors = {course.id: teacher_colors[course.teacher.id] for course in unique_courses}
    return render(request, 'database/schedule.html', {
        'groups':        groups,
        'rows':          rows,
        'page_obj':      page_obj,
        'start_week':    start_week,
        'end_week':      end_week,
        'course_colors': course_colors,  # передаємо до шаблону
    })