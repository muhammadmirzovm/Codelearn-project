"""
Unit tests for core CodeLearn features.

Run with: python manage.py test
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.users.models import Group
from apps.tasks.models import Task, TestCase as TC
from apps.sessions_app.models import Session
from apps.submissions.models import Submission
from apps.runner.services import run_code_sync

User = get_user_model()


class UserModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='t1', password='pass', role='teacher'
        )
        self.student = User.objects.create_user(
            username='s1', password='pass', role='student'
        )

    def test_teacher_flag(self):
        self.assertTrue(self.teacher.is_teacher)
        self.assertFalse(self.teacher.is_student)

    def test_student_flag(self):
        self.assertTrue(self.student.is_student)
        self.assertFalse(self.student.is_teacher)


class GroupTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='t2', password='p', role='teacher')
        self.student = User.objects.create_user(username='s2', password='p', role='student')
        self.group = Group.objects.create(name='G1', teacher=self.teacher)
        self.group.students.add(self.student)

    def test_student_in_group(self):
        self.assertIn(self.student, self.group.students.all())

    def test_group_str(self):
        self.assertIn('G1', str(self.group))


class TaskCreationTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='t3', password='p', role='teacher')
        self.client = Client()
        self.client.login(username='t3', password='p')

    def test_create_task_view(self):
        url = reverse('tasks:task_create')
        data = {
            'title': 'Hello World',
            'description': 'Print hello',
            'example_input': '',
            'example_output': 'hello',
            'time_limit': 5,
            'memory_limit': '64m',
            # Formset management fields
            'test_cases-TOTAL_FORMS': '1',
            'test_cases-INITIAL_FORMS': '0',
            'test_cases-MIN_NUM_FORMS': '0',
            'test_cases-MAX_NUM_FORMS': '1000',
            'test_cases-0-input_data': '',
            'test_cases-0-expected_output': 'hello',
            'test_cases-0-is_example': 'on',
            'test_cases-0-order': '0',
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Task.objects.filter(title='Hello World').exists())


class RunnerTest(TestCase):
    """Tests for the synchronous code runner."""

    def _make_tc(self, input_data, expected_output, is_example=True):
        """Create a mock test case object."""
        class MockTC:
            pass
        tc = MockTC()
        tc.pk = 1
        tc.input_data = input_data
        tc.expected_output = expected_output
        tc.is_example = is_example
        return tc

    def test_correct_code(self):
        tc = self._make_tc('3\n7\n', '10')
        code = 'a=int(input()); b=int(input()); print(a+b)'
        results = run_code_sync(code, [tc], time_limit=5, memory_limit='64m')
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]['passed'])

    def test_wrong_output(self):
        tc = self._make_tc('3\n7\n', '10')
        code = 'print(99)'
        results = run_code_sync(code, [tc], time_limit=5, memory_limit='64m')
        self.assertFalse(results[0]['passed'])

    def test_syntax_error(self):
        tc = self._make_tc('', 'hello')
        code = 'def broken(:'
        results = run_code_sync(code, [tc], time_limit=5, memory_limit='64m')
        self.assertFalse(results[0]['passed'])
        self.assertNotEqual(results[0]['exit_code'], 0)

    def test_timeout(self):
        tc = self._make_tc('', '')
        code = 'import time; time.sleep(999)'
        results = run_code_sync(code, [tc], time_limit=1, memory_limit='64m')
        self.assertFalse(results[0]['passed'])
        self.assertEqual(results[0]['error'], 'TLE')


class LeaderboardOrderingTest(TestCase):
    """Test that leaderboard sorts passed-first, then by time."""

    def setUp(self):
        self.teacher = User.objects.create_user(username='t4', password='p', role='teacher')
        self.s1 = User.objects.create_user(username='s_a', password='p', role='student')
        self.s2 = User.objects.create_user(username='s_b', password='p', role='student')
        self.group = Group.objects.create(name='LB', teacher=self.teacher)
        self.group.students.add(self.s1, self.s2)
        self.task = Task.objects.create(
            title='T', description='d', created_by=self.teacher
        )
        self.session = Session.objects.create(
            group=self.group, task=self.task,
            start_time='2025-01-01T10:00:00Z', is_active=True
        )

    def test_passed_student_ranks_first(self):
        # s1 submitted and passed; s2 submitted but failed
        Submission.objects.create(
            student=self.s1, task=self.task, session=self.session,
            code='', is_correct=True, status='passed'
        )
        Submission.objects.create(
            student=self.s2, task=self.task, session=self.session,
            code='', is_correct=False, status='failed'
        )
        students = self.group.students.all()
        board = []
        for student in students:
            subs = Submission.objects.filter(student=student, session=self.session).order_by('created_at')
            best = subs.filter(is_correct=True).first()
            board.append({'student': student, 'passed': best is not None, 'submitted_at': best.created_at if best else None})
        board.sort(key=lambda x: (not x['passed'], x['submitted_at'] or '9999'))
        self.assertEqual(board[0]['student'], self.s1)
