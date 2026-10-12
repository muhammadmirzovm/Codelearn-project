from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import RegisterForm
from .models import User


@override_settings(LANGUAGE_CODE='en')
class RegistrationCollisionTests(TestCase):
    def setUp(self):
        self.data = {
            'username': 'registration_user',
            'email': 'registration@example.com',
            'first_name': 'Registration',
            'last_name': 'User',
            'role': User.STUDENT,
            'password1': 'A-private-test-password-972!',
            'password2': 'A-private-test-password-972!',
        }
        self.url = reverse('users:register')

    def test_existing_username_shows_field_error(self):
        User.objects.create_user(username=self.data['username'])
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('username', response.context['form'].errors)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_username_claimed_after_validation_does_not_crash(self):
        form = RegisterForm(data=self.data)
        self.assertTrue(form.is_valid(), form.errors)
        existing = User.objects.create_user(username=self.data['username'])
        with patch('apps.users.views.RegisterForm', return_value=form):
            response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('username', response.context['form'].errors)
        self.assertEqual(User.objects.get(username=self.data['username']).pk, existing.pk)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unrelated_database_error_is_not_hidden(self):
        with patch.object(RegisterForm, 'save', side_effect=IntegrityError('Other constraint')):
            with self.assertRaises(IntegrityError):
                self.client.post(self.url, self.data)

    def test_new_user_can_still_register(self):
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username=self.data['username'])
        self.assertEqual(user.role, User.STUDENT)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
