from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

PASSWORD = "Vr7!long-pass"


class RegisterTests(TestCase):
    url = reverse("accounts:register")

    def register(self, **overrides):
        data = {"username": "lina", "email": "lina@example.test", "password1": PASSWORD, "password2": PASSWORD}
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_register_creates_user_and_logs_in(self):
        response = self.register()

        self.assertRedirects(response, reverse("trips:my_trips"))
        user = User.objects.get(username="lina")
        self.assertNotEqual(user.password, PASSWORD)  # stored hashed by Django, never as plain text
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user("lina", password=PASSWORD)

        self.assertContains(self.register(), "A user with that username already exists.")
        self.assertEqual(User.objects.count(), 1)

    def test_email_is_required(self):
        self.register(email="")

        self.assertFalse(User.objects.filter(username="lina").exists())

    def test_mismatched_passwords_are_rejected(self):
        self.register(password2="something-else-123")

        self.assertFalse(User.objects.exists())

    def test_logged_in_user_is_redirected_away(self):
        self.client.force_login(User.objects.create_user("lina", password=PASSWORD))

        self.assertRedirects(self.client.get(self.url), reverse("trips:my_trips"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        User.objects.create_user("lina", password=PASSWORD)

    def test_login_redirects_to_my_trips(self):
        response = self.client.post(reverse("accounts:login"), {"username": "lina", "password": PASSWORD})

        self.assertRedirects(response, reverse("trips:my_trips"))

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse("accounts:login"), {"username": "lina", "password": "wrong"})

        self.assertContains(response, "Please enter a correct username and password.")

    def test_logout_requires_post_and_ends_session(self):
        self.client.login(username="lina", password=PASSWORD)
        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("trips:home"))
        self.assertNotIn("_auth_user_id", self.client.session)
