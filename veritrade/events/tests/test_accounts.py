"""Registration, email login, uploads, and the top-up endpoint."""

from django.test import TestCase, override_settings
from django.urls import reverse

from events.models import CreditAccount, Role, UserProfile
from events.services import credits

from .factories import PASSWORD, make_user, tiny_image


class SignupTests(TestCase):
    def _payload(self, **overrides):
        data = {
            "first_name": "New",
            "last_name": "Person",
            "username": "newperson",
            "email": "new@example.test",
            "phone_number": "+447700900123",
            "password1": "correct-horse-9",
            "password2": "correct-horse-9",
        }
        data.update(overrides)
        return data

    def test_signup_creates_a_member_with_profile_and_account(self):
        response = self.client.post(reverse("accounts:signup"), self._payload())
        self.assertEqual(response.status_code, 302)

        profile = UserProfile.objects.get(user__username="newperson")
        self.assertEqual(profile.role, Role.MEMBER)
        self.assertTrue(CreditAccount.objects.filter(user=profile.user).exists())

    def test_evaluator_signup_sets_the_role(self):
        self.client.post(reverse("accounts:signup_evaluator"), self._payload())
        self.assertEqual(
            UserProfile.objects.get(user__username="newperson").role, Role.EVALUATOR
        )

    def test_duplicate_email_is_rejected(self):
        make_user(username="existing", email="taken@example.test")
        response = self.client.post(
            reverse("accounts:signup"), self._payload(email="taken@example.test")
        )
        self.assertEqual(response.status_code, 200)  # re-rendered with errors
        self.assertFalse(UserProfile.objects.filter(user__username="newperson").exists())

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse("accounts:signup"),
            self._payload(password1="password", password2="password"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserProfile.objects.filter(user__username="newperson").exists())


class LoginTests(TestCase):
    def setUp(self):
        self.profile = make_user(username="loginuser", email="login@example.test")

    def test_login_with_email_succeeds(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "login@example.test", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 302)

    def test_login_is_case_insensitive_in_the_email(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "LOGIN@EXAMPLE.TEST", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 302)

    def test_wrong_password_stays_on_the_form(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "login@example.test", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 200)

    def test_the_database_refuses_a_duplicate_email(self):
        """The case-insensitive unique index is the real guard against the
        original 'two accounts, one email' bug, so login can trust that an
        email resolves to at most one account."""
        from django.contrib.auth.models import User
        from django.db import IntegrityError, transaction

        User.objects.filter(pk=self.profile.user.pk).update(email="dup@example.test")
        second = make_user(username="second")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.filter(pk=second.user.pk).update(
                    email="DUP@example.test"  # differing case must still collide
                )


class WalletTests(TestCase):
    def setUp(self):
        self.profile = make_user(username="walletuser")
        self.client.login(username="walletuser", password=PASSWORD)

    def test_top_up_adds_credits(self):
        self.client.post(reverse("accounts:wallet"), {"amount": 250})
        self.assertEqual(credits.get_balance(self.profile.user), 250)

    def test_negative_top_up_is_rejected_by_the_form(self):
        self.client.post(reverse("accounts:wallet"), {"amount": -100})
        self.assertEqual(credits.get_balance(self.profile.user), 0)

    @override_settings(MAX_TOPUP_CREDITS=1000)
    def test_top_up_over_the_cap_is_rejected(self):
        self.client.post(reverse("accounts:wallet"), {"amount": 5000})
        self.assertEqual(credits.get_balance(self.profile.user), 0)


class UploadValidationTests(TestCase):
    def setUp(self):
        self.profile = make_user(username="seller1")
        self.client.login(username="seller1", password=PASSWORD)

    def _listing_payload(self):
        return {
            "name": "Test camera",
            "category": "CAM_CORD",
            "description": "A camera listed during a test of upload validation.",
            "purchase_price": 500,
            "listed_price": 300,
            "discount_percent": 0,
        }

    def test_a_non_image_upload_is_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake = SimpleUploadedFile(
            "malware.docx", b"PK\x03\x04 not an image",
            content_type="application/vnd.openxmlformats",
        )
        response = self.client.post(
            reverse("marketplace:sell"),
            {**self._listing_payload(), "image_1": fake},
        )
        self.assertEqual(response.status_code, 200)  # re-rendered with the error
        from events.models import Product

        self.assertFalse(Product.objects.filter(name="Test camera").exists())

    def test_a_real_image_is_accepted(self):
        response = self.client.post(
            reverse("marketplace:sell"),
            {**self._listing_payload(), "image_1": tiny_image()},
        )
        self.assertEqual(response.status_code, 302)
        from events.models import Product

        product = Product.objects.get(name="Test camera")
        self.assertEqual(product.seller, self.profile)
        self.assertEqual(product.images.count(), 1)
