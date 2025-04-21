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
                return redirect('dashboard')
        else:
            messages.error(request, "Невірне ім'я користувача або пароль.")
    return render(request, 'database/login.html')

def logout_view(request):
    logout(request)
    return  render(request, 'database/login.html')

import datetime

@login_required(login_url='login')
def dashboard(request):
    subgroup_id = request.GET.get('subgroup')
    date_str = request.GET.get('date')

    if subgroup_id and date_str:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_obj = datetime.date.today()
        lessons = Lesson.objects.filter(
            subgroup__id=subgroup_id,
            date=date_obj
        ).order_by('course__course_name').distinct('course__course_name')[:10]
    else:
        lessons = None  # або можна використовувати Lesson.objects.none()

    # Отримуємо список усіх підгруп для формування випадаючого списку
    subgroups = Subgroup.objects.all()

    context = {
        'user': request.user,
        'lessons': lessons,
        'subgroups': subgroups,
        # інші дані для відображення на сторінці можна додати сюди
    }
    return render(request, 'database/dashboard.html', context)