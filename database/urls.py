from django.contrib import admin
from django.urls import path
from . import views
from .views import schedule_view

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),

    path('logout/', views.logout_view, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),

    path('schedule/', schedule_view, name='schedule')
]
