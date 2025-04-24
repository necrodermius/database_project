from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from datetime import date, time

from database.models import (
    StudyPlan, Teacher, Course,
    Group, Subgroup, Lesson
)

class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user', password='pass')

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('login'))

    def test_home_with_login(self):
        self.client.login(username='user', password='pass')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'database/home.html')


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = 'secret123'
        self.student = User.objects.create_user(username='stu', password=self.password)
        self.staff = User.objects.create_user(
            username='staff', password=self.password, is_staff=True
        )

    def test_get_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'database/login.html')

    def test_post_invalid_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'wrong', 'password': 'bad'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'database/login.html')
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(
            "Невірне ім'я користувача або пароль." in str(m)
            for m in messages
        ))

    def test_post_valid_student(self):
        response = self.client.post(reverse('login'), {
            'username': 'stu', 'password': self.password
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_post_valid_staff(self):
        response = self.client.post(reverse('login'), {
            'username': 'staff', 'password': self.password
        })
        # Redirects to /admin/ for staff
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/admin/')


class LogoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='u', password='pass')
        self.client.login(username='u', password='pass')

    def test_logout_renders_login(self):
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'database/login.html')
        # Afterwards, protected page redirects to login
        resp2 = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            resp2,
            f"{reverse('login')}?next={reverse('dashboard')}"
        )


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='u', password='pass')
        # Create minimal schedule data
        self.plan = StudyPlan.objects.create(
            name='P', year_of_effect=2022,
            number_of_semesters=2,
            approval_date=date(2022,1,1), plan_author='A'
        )
        self.teacher = Teacher.objects.create(
            full_name='T', position='Prof',
            allowed_hours=10, rate=1.0
        )
        self.course = Course.objects.create(
            study_plan=self.plan,
            course_name='C1', lecture_hours=1,
            practice_hours=1, semester=1,
            credits=1, teacher=self.teacher
        )
        self.group = Group.objects.create(
            name='G1', major='M', year=1,
            start_year=2022, study_plan=self.plan
        )
        self.subgroup = Subgroup.objects.create(
            group=self.group, number=1
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            subgroup=self.subgroup,
            date=date(2022,1,5),
            start_time=time(9,0),
            lesson_type='Lab'
        )

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            resp,
            f"{reverse('login')}?next={reverse('dashboard')}"
        )

    def test_dashboard_no_params(self):
        self.client.login(username='u', password='pass')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context.get('lessons'))

    def test_dashboard_with_valid_params(self):
        self.client.login(username='u', password='pass')
        resp = self.client.get(
            reverse('dashboard'),
            {'subgroup': self.subgroup.id, 'date': '2022-01-05'}
        )
        self.assertEqual(resp.status_code, 200)
        lessons = resp.context.get('lessons')
        self.assertTrue(lessons is not None and len(lessons) == 1)
        if lessons:
            self.assertEqual(lessons[0], self.lesson)


    def test_dashboard_invalid_date(self):
        self.client.login(username='u', password='pass')
        resp = self.client.get(
            reverse('dashboard'),
            {'subgroup': self.subgroup.id, 'date': 'invalid'}
        )
        self.assertEqual(resp.status_code, 200)
        # Should gracefully handle invalid date => no lessons or None
        lessons = resp.context.get('lessons')
        self.assertTrue(lessons is None or not lessons.exists())

class ScheduleViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create minimal schedule data for one week
        self.plan = StudyPlan.objects.create(
            name='P', year_of_effect=2022,
            number_of_semesters=2,
            approval_date=date(2022,1,1), plan_author='A'
        )
        self.teacher = Teacher.objects.create(
            full_name='T', position='Prof',
            allowed_hours=10, rate=1.0
        )
        self.course = Course.objects.create(
            study_plan=self.plan,
            course_name='C1', lecture_hours=1,
            practice_hours=1, semester=1,
            credits=1, teacher=self.teacher
        )
        self.group = Group.objects.create(
            name='G1', major='M', year=1,
            start_year=2022, study_plan=self.plan
        )
        self.subgroup = Subgroup.objects.create(
            group=self.group, number=1
        )
        # Monday of a known week
        self.lesson = Lesson.objects.create(
            course=self.course,
            subgroup=self.subgroup,
            date=date(2022,1,3),
            start_time=time(9,0),
            lesson_type='Lecture'
        )

    def test_schedule_empty_when_no_lessons(self):
        # Clear lessons
        Lesson.objects.all().delete()
        resp = self.client.get(reverse('schedule'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['groups'], [])
        self.assertEqual(resp.context['rows'], [])

    def test_schedule_weekly_output(self):
        resp = self.client.get(reverse('schedule'))
        self.assertEqual(resp.status_code, 200)
        ctx = resp.context
        # One group with one subgroup
        self.assertEqual(len(ctx['groups']), 1)
        # 7 rows, since one timeslot across 7 days
        self.assertEqual(len(ctx['rows']), 7)
        # The lesson appears on the correct day
        monday_row = next(r for r in ctx['rows'] if r['day'] == date(2022,1,3))
        self.assertIsNotNone(monday_row['cells'][0])
        self.assertEqual(monday_row['cells'][0].id, self.lesson.id)
        # Course color mapping exists
        self.assertIn(self.course.id, ctx['course_colors'])
        # Only one page
        self.assertEqual(ctx['page_obj'].paginator.num_pages, 1)
        # Template used
        self.assertTemplateUsed(resp, 'database/schedule.html')
