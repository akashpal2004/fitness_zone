import base64
import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Address,
    Contact,
    Gender,
    Gym_split,
    Gym_user,
    Membership,
    MembershipStatus,
    Muscle_strength,
    PaymentProof,
    PaymentStatus,
)


PNG_IMAGE_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEElEQVR4nGP8zwACTGCSAQANHQEDgslx/wAAAABJRU5ErkJggg=="
)


class MemberRouteAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.address = Address.objects.create(area="Kulhan")
        cls.alt_address = Address.objects.create(area="Jakhan")
        cls.gender_male = Gender.objects.create(gender="Male")
        cls.gender_female = Gender.objects.create(gender="Female")
        cls.gym_split_5 = Gym_split.objects.create(split_name="5 Day Split")
        cls.gym_split_3 = Gym_split.objects.create(split_name="3 Day Split (PPL)")
        cls.strength_beginner = Muscle_strength.objects.create(type="Beginner")
        cls.strength_intermediate = Muscle_strength.objects.create(type="Intermediate")

        cls.member_user = User.objects.create_user(
            username="rahul",
            password="secret123",
            first_name="Rahul",
            last_name="Sharma",
            email="rahul@example.com",
        )
        cls.member = Gym_user.objects.create(
            user=cls.member_user,
            first_name="Rahul",
            last_name="Sharma",
            dob="1998-01-01",
            phone_number=9876543210,
            weight=72,
            height=175,
            email="rahul@example.com",
            username="rahul",
            password="",
            address=cls.address,
            gender=cls.gender_male,
            gym_split=cls.gym_split_5,
            muscle_strength=cls.strength_beginner,
        )

        cls.other_member_user = User.objects.create_user(
            username="aman",
            password="secret123",
            first_name="Aman",
            last_name="Verma",
            email="aman@example.com",
        )
        cls.other_member = Gym_user.objects.create(
            user=cls.other_member_user,
            first_name="Aman",
            last_name="Verma",
            dob="1997-02-02",
            phone_number=9876543211,
            weight=78,
            height=180,
            email="aman@example.com",
            username="aman",
            password="",
            address=cls.address,
            gender=cls.gender_male,
            gym_split=cls.gym_split_5,
            muscle_strength=cls.strength_beginner,
        )

        cls.staff_user = User.objects.create_user(
            username="gymadmin",
            password="admin12345",
            first_name="Gym",
            last_name="Admin",
            email="admin@example.com",
            is_staff=True,
            is_superuser=True,
        )

    def _login_member(self, user_account):
        self.client.force_login(user_account)

    def _login_admin(self):
        self.client.force_login(self.staff_user)

    def _registration_payload(self, **overrides):
        payload = {
            "first_name": "Sana",
            "last_name": "Bisht",
            "dob": "2001-07-11",
            "phone_number": "9876543224",
            "height": "168",
            "weight": "59",
            "username": "sana",
            "password1": "FitPass123!",
            "password2": "FitPass123!",
            "muscle_strength": "Beginner",
            "gym_split": "3 Day Split (PPL)",
            "gender": "Female",
            "address": "Kulhan",
            "email": "sana@example.com",
            "accept_terms": "on",
        }
        payload.update(overrides)
        return payload

    def _png_upload(self, filename="proof.png"):
        return SimpleUploadedFile(filename, PNG_IMAGE_BYTES, content_type="image/png")

    def _create_membership_submission(
        self,
        *,
        plan_name="Monthly",
        amount="999.00",
        duration=30,
        payment_status=PaymentStatus.PENDING,
        membership_status=MembershipStatus.PENDING,
        utr_number="UTR12345678",
    ):
        membership = Membership.objects.create(
            user=self.member_user,
            plan_name=plan_name,
            amount=amount,
            duration=duration,
            payment_status=payment_status,
            membership_status=membership_status,
        )
        payment_proof = PaymentProof.objects.create(
            user=self.member_user,
            membership=membership,
            screenshot=self._png_upload(f"{plan_name.lower()}-proof.png"),
            utr_number=utr_number,
            payment_status=payment_status,
        )
        return membership, payment_proof

    def test_anonymous_user_is_redirected_from_member_routes(self):
        expected_redirects = {
            "/profile_page": "/login?next=%2Fprofile_page",
            "/diet_plan": "/login?next=%2Fdiet_plan",
            "/workout_plan": "/login?next=%2Fworkout_plan",
            "/workout": "/login?next=%2Fworkout",
        }

        for path, redirect_url in expected_redirects.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertRedirects(response, redirect_url)

    def test_membership_page_is_public(self):
        response = self.client.get("/membership")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose The")
        self.assertContains(response, "Membership")
        self.assertContains(response, "Monthly")
        self.assertContains(response, "Quarterly")
        self.assertContains(response, "Yearly")
        self.assertContains(response, "Most Popular")

    def test_home_page_links_to_membership_page(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/membership"')

    def test_logged_in_member_can_open_payment_page(self):
        self._login_member(self.member_user)

        response = self.client.get("/payment/yearly")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Yearly Plan")
        self.assertContains(response, "Rs 8,999")
        self.assertContains(response, "Pay Now")

    def test_payment_page_requires_login_and_preserves_next(self):
        response = self.client.get("/payment/monthly")

        self.assertRedirects(response, "/login?next=%2Fpayment%2Fmonthly")

    def test_login_page_is_not_cached(self):
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-cache", response.headers.get("Cache-Control", ""))
        self.assertIn("max-age=0", response.headers.get("Cache-Control", ""))

    def test_stale_csrf_login_submission_redirects_back_with_message(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.get("/login")

        response = csrf_client.post(
            "/login",
            {
                "username": self.member_user.username,
                "password": "secret123",
                "csrfmiddlewaretoken": "stale-token",
            },
            HTTP_REFERER="http://testserver/login",
            follow=True,
        )

        self.assertRedirects(response, "http://testserver/login")
        self.assertContains(
            response,
            "Your form session expired or became outdated. Please try again with the refreshed page.",
        )

    def test_join_membership_redirects_logged_in_member_to_payment_page(self):
        self._login_member(self.member_user)

        response = self.client.get("/membership/join/quarterly")

        self.assertRedirects(response, "/payment/quarterly")

    def test_join_membership_redirects_anonymous_member_to_login_with_next(self):
        response = self.client.get("/membership/join/quarterly")

        self.assertRedirects(response, "/login?next=%2Fpayment%2Fquarterly")

    def test_login_redirects_to_requested_payment_page(self):
        response = self.client.post(
            "/login",
            {
                "username": self.member_user.username,
                "password": "secret123",
                "next": "/payment/monthly",
            },
        )

        self.assertRedirects(response, "/payment/monthly")

    def test_registration_with_next_redirects_to_payment_page(self):
        response = self.client.post(
            "/new_registration",
            self._registration_payload(next="/payment/yearly"),
        )

        self.assertRedirects(response, "/payment/yearly")
        created_profile = Gym_user.objects.get(username="sana")
        session = self.client.session
        self.assertEqual(int(session["_auth_user_id"]), created_profile.user_id)

    def test_member_can_submit_manual_upi_payment(self):
        self._login_member(self.member_user)
        test_media_root = Path(settings.BASE_DIR) / "test_media_payments"
        shutil.rmtree(test_media_root, ignore_errors=True)
        test_media_root.mkdir(parents=True, exist_ok=True)

        try:
            with self.settings(MEDIA_ROOT=str(test_media_root)):
                response = self.client.post(
                    "/payment/monthly",
                    {
                        "screenshot": self._png_upload("monthly-proof.png"),
                        "utr_number": "UTR00000001",
                    },
                    follow=True,
                )

                self.assertRedirects(response, "/payment/monthly")
                membership = Membership.objects.get(user=self.member_user, plan_name="Monthly")
                payment_proof = PaymentProof.objects.get(membership=membership)

                self.assertEqual(membership.payment_status, PaymentStatus.PENDING)
                self.assertEqual(membership.membership_status, MembershipStatus.PENDING)
                self.assertEqual(membership.duration, 30)
                self.assertEqual(payment_proof.payment_status, PaymentStatus.PENDING)
                self.assertContains(
                    response,
                    "Payment submitted successfully. Waiting for admin verification.",
                )
        finally:
            shutil.rmtree(test_media_root, ignore_errors=True)

    def test_payment_page_blocks_duplicate_pending_submission_for_same_plan(self):
        self._login_member(self.member_user)
        test_media_root = Path(settings.BASE_DIR) / "test_media_payments"
        shutil.rmtree(test_media_root, ignore_errors=True)
        test_media_root.mkdir(parents=True, exist_ok=True)

        try:
            with self.settings(MEDIA_ROOT=str(test_media_root)):
                self.client.post(
                    "/payment/monthly",
                    {
                        "screenshot": self._png_upload("monthly-proof.png"),
                        "utr_number": "UTR00000002",
                    },
                )

                response = self.client.post(
                    "/payment/monthly",
                    {
                        "screenshot": self._png_upload("monthly-proof-second.png"),
                        "utr_number": "UTR00000003",
                    },
                    follow=True,
                )

                self.assertRedirects(response, "/payment/monthly")
                self.assertEqual(Membership.objects.filter(user=self.member_user, plan_name="Monthly").count(), 1)
                self.assertEqual(PaymentProof.objects.filter(user=self.member_user).count(), 1)
                self.assertContains(
                    response,
                    "You already have a payment awaiting verification for this membership plan.",
                )
        finally:
            shutil.rmtree(test_media_root, ignore_errors=True)

    def test_approved_payment_activates_membership_automatically(self):
        test_media_root = Path(settings.BASE_DIR) / "test_media_payments"
        shutil.rmtree(test_media_root, ignore_errors=True)
        test_media_root.mkdir(parents=True, exist_ok=True)

        try:
            with self.settings(MEDIA_ROOT=str(test_media_root)):
                membership, payment_proof = self._create_membership_submission(
                    plan_name="Quarterly",
                    amount="2499.00",
                    duration=90,
                    utr_number="UTRAPPROVED01",
                )
                payment_proof.approve(admin_note="Verified manually by admin.")

                membership.refresh_from_db()
                payment_proof.refresh_from_db()

                self.assertEqual(payment_proof.payment_status, PaymentStatus.APPROVED)
                self.assertEqual(membership.payment_status, PaymentStatus.APPROVED)
                self.assertEqual(membership.membership_status, MembershipStatus.ACTIVE)
                self.assertEqual(membership.start_date, timezone.localdate())
                self.assertEqual(membership.expiry_date, timezone.localdate() + timedelta(days=90))
                self.assertEqual(payment_proof.admin_note, "Verified manually by admin.")
        finally:
            shutil.rmtree(test_media_root, ignore_errors=True)

    def test_rejected_payment_marks_membership_inactive(self):
        test_media_root = Path(settings.BASE_DIR) / "test_media_payments"
        shutil.rmtree(test_media_root, ignore_errors=True)
        test_media_root.mkdir(parents=True, exist_ok=True)

        try:
            with self.settings(MEDIA_ROOT=str(test_media_root)):
                membership, payment_proof = self._create_membership_submission(
                    plan_name="Yearly",
                    amount="8999.00",
                    duration=365,
                    utr_number="UTRREJECTED1",
                )
                payment_proof.reject(admin_note="Amount mismatch.")

                membership.refresh_from_db()
                payment_proof.refresh_from_db()

                self.assertEqual(payment_proof.payment_status, PaymentStatus.REJECTED)
                self.assertEqual(membership.payment_status, PaymentStatus.REJECTED)
                self.assertEqual(membership.membership_status, MembershipStatus.INACTIVE)
                self.assertIsNone(membership.start_date)
                self.assertIsNone(membership.expiry_date)
                self.assertEqual(payment_proof.admin_note, "Amount mismatch.")
        finally:
            shutil.rmtree(test_media_root, ignore_errors=True)

    def test_profile_page_displays_membership_dashboard(self):
        self._login_member(self.member_user)
        test_media_root = Path(settings.BASE_DIR) / "test_media_payments"
        shutil.rmtree(test_media_root, ignore_errors=True)
        test_media_root.mkdir(parents=True, exist_ok=True)

        try:
            with self.settings(MEDIA_ROOT=str(test_media_root)):
                membership, payment_proof = self._create_membership_submission(
                    plan_name="Monthly",
                    utr_number="UTRDASHBOARD1",
                )
                payment_proof.approve(admin_note="Approved for dashboard test.")
                membership.refresh_from_db()

                response = self.client.get("/profile_page")

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Membership Dashboard")
                self.assertContains(response, "Monthly")
                self.assertContains(response, "UTRDASHBOARD1")
                self.assertContains(response, "Active")
        finally:
            shutil.rmtree(test_media_root, ignore_errors=True)

    def test_logged_in_member_can_use_profile_routes(self):
        self._login_member(self.member_user)

        profile_response = self.client.get("/profile_page")
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.context["user"], self.member)

        workout_plan_response = self.client.get("/workout_plan")
        self.assertEqual(workout_plan_response.status_code, 200)
        self.assertEqual(workout_plan_response.context["user"], self.member)

        workout_response = self.client.get("/workout")
        self.assertEqual(workout_response.status_code, 200)
        self.assertEqual(workout_response.context["user"], self.member)

        diet_response = self.client.get("/diet_plan")
        self.assertEqual(diet_response.status_code, 200)
        self.assertEqual(diet_response.context["user"], self.member)

    def test_member_cannot_access_another_members_pages_by_query_string(self):
        self._login_member(self.member_user)

        for path in (
            f"/profile_page?u_id={self.other_member.id}",
            f"/diet_plan?pid={self.other_member.id}",
            f"/workout_plan?pid={self.other_member.id}",
            f"/workout?pid={self.other_member.id}",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertRedirects(response, "/profile_page")

    def test_admin_can_open_member_workout_pages_with_query_string(self):
        self._login_admin()

        for path in (
            f"/profile_page?u_id={self.member.id}",
            f"/diet_plan?pid={self.member.id}",
            f"/workout_plan?pid={self.member.id}",
            f"/workout?pid={self.member.id}",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_registration_logs_in_member_immediately(self):
        response = self.client.post(
            "/new_registration",
            self._registration_payload(
                first_name="Priya",
                last_name="Negi",
                email="priya@example.com",
                username="priya",
                gym_split="5 Day Split",
            ),
        )

        self.assertRedirects(response, "/profile_page")
        created_profile = Gym_user.objects.get(username="priya")
        session = self.client.session
        self.assertEqual(int(session["_auth_user_id"]), created_profile.user_id)
        self.assertEqual(created_profile.user.username, "priya")
        self.assertTrue(created_profile.user.check_password("FitPass123!"))

    def test_admin_registration_keeps_admin_session(self):
        self._login_admin()

        response = self.client.post(
            "/new_registration",
            self._registration_payload(
                first_name="Karan",
                last_name="Rawat",
                email="karan@example.com",
                username="karan",
                gender="Male",
                address="Jakhan",
                muscle_strength="Intermediate",
            ),
            follow=True,
        )

        self.assertRedirects(response, "/new_registration")
        self.assertTrue(Gym_user.objects.filter(username="karan").exists())
        self.assertContains(response, "was registered successfully")
        session = self.client.session
        self.assertEqual(int(session["_auth_user_id"]), self.staff_user.id)

    def test_public_registration_requires_accepting_terms(self):
        response = self.client.post(
            "/new_registration",
            self._registration_payload(
                username="termsmissing",
                email="termsmissing@example.com",
                accept_terms="",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Gym_user.objects.filter(username="termsmissing").exists())
        self.assertContains(response, "Please accept the Terms &amp; Conditions and Privacy Policy.")

    def test_admin_registration_does_not_require_terms_checkbox(self):
        self._login_admin()

        response = self.client.post(
            "/new_registration",
            self._registration_payload(
                first_name="Neeraj",
                last_name="Kandari",
                email="neeraj@example.com",
                username="neeraj",
                gender="Male",
                accept_terms="",
            ),
            follow=True,
        )

        self.assertRedirects(response, "/new_registration")
        self.assertTrue(Gym_user.objects.filter(username="neeraj").exists())

    def test_profile_page_contains_profile_picture_upload_controls(self):
        self._login_member(self.member_user)

        response = self.client.get("/profile_page")

        self.assertContains(response, 'id="avatar-container"')
        self.assertContains(response, 'id="open-upload-btn"')
        self.assertContains(response, 'id="image-upload"')

    def test_member_can_upload_profile_picture(self):
        self._login_member(self.member_user)
        test_media_root = Path(settings.BASE_DIR) / "test_media_uploads"
        shutil.rmtree(test_media_root, ignore_errors=True)
        test_media_root.mkdir(parents=True, exist_ok=True)

        try:
            with self.settings(MEDIA_ROOT=str(test_media_root)):
                upload = SimpleUploadedFile("avatar.png", PNG_IMAGE_BYTES, content_type="image/png")
                response = self.client.post(
                    "/upload_profile_image/",
                    {"user_id": self.member.id, "image": upload},
                )

                self.assertEqual(response.status_code, 200)
                self.member.refresh_from_db()
                self.assertJSONEqual(
                    response.content,
                    {
                        "success": True,
                        "message": "Profile picture updated successfully!",
                        "image_url": self.member.image.url,
                    },
                )
                self.assertNotEqual(self.member.image.name, "users_profile_images/image.png")
                self.member.image.delete(save=False)
        finally:
            shutil.rmtree(test_media_root, ignore_errors=True)

    def test_member_cannot_upload_other_members_profile_picture(self):
        self._login_member(self.member_user)
        test_media_root = Path(settings.BASE_DIR) / "test_media_uploads"
        shutil.rmtree(test_media_root, ignore_errors=True)
        test_media_root.mkdir(parents=True, exist_ok=True)

        try:
            with self.settings(MEDIA_ROOT=str(test_media_root)):
                upload = SimpleUploadedFile("avatar.png", PNG_IMAGE_BYTES, content_type="image/png")
                response = self.client.post(
                    "/upload_profile_image/",
                    {"user_id": self.other_member.id, "image": upload},
                )

                self.assertEqual(response.status_code, 403)
                self.assertJSONEqual(
                    response.content,
                    {
                        "success": False,
                        "message": "You are not authorized to update this profile.",
                    },
                )
        finally:
            shutil.rmtree(test_media_root, ignore_errors=True)

    def test_admin_login_requires_staff_account(self):
        response = self.client.post(
            "/admin_login",
            {
                "username": self.member_user.username,
                "password": "secret123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not have administrator access")


class ContactFlowTests(TestCase):
    def test_contact_page_renders_form(self):
        response = self.client.get("/contact")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="subject"')
        self.assertContains(response, 'name="message"')

    def test_valid_contact_submission_is_saved_and_emailed(self):
        with self.settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="noreply@example.com",
            CONTACT_NOTIFICATION_EMAIL="owner@example.com",
        ):
            response = self.client.post(
                "/contact",
                {
                    "name": "Aarav Singh",
                    "email": "aarav@example.com",
                    "subject": "Membership enquiry",
                    "message": "I would like to know more about your yearly membership plan.",
                    "website": "",
                },
                follow=True,
            )

        self.assertRedirects(response, "/contact")
        self.assertEqual(Contact.objects.count(), 1)

        saved_message = Contact.objects.get()
        self.assertEqual(saved_message.name, "Aarav Singh")
        self.assertEqual(saved_message.email, "aarav@example.com")
        self.assertEqual(saved_message.subject, "Membership enquiry")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn("Membership enquiry", mail.outbox[0].subject)
        self.assertIn(saved_message.message, mail.outbox[0].body)
        self.assertContains(
            response,
            "Thank you for contacting FitnessPro. Your message has been sent successfully.",
        )

    def test_invalid_contact_submission_shows_validation_errors(self):
        response = self.client.post(
            "/contact",
            {
                "name": "A1",
                "email": "invalid-email",
                "subject": "Hi",
                "message": "Short",
                "website": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), 0)
        self.assertContains(response, "Please correct the errors below and submit the form again.")
        self.assertContains(response, "Name cannot contain numbers.")
        self.assertContains(response, "Enter a valid email address.")
        self.assertContains(response, "Subject must be at least 3 characters long.")
        self.assertContains(response, "Message must be at least 10 characters long.")


class PaymentAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(
            username="staffadmin",
            password="admin12345",
            email="staff@example.com",
            is_staff=True,
            is_superuser=True,
        )
        cls.member_user = User.objects.create_user(
            username="paymentmember",
            password="secret123",
            email="member@example.com",
        )
        cls.membership = Membership.objects.create(
            user=cls.member_user,
            plan_name="Quarterly",
            amount="2499.00",
            duration=90,
            payment_status=PaymentStatus.PENDING,
            membership_status=MembershipStatus.PENDING,
        )
        cls.payment_proof = PaymentProof.objects.create(
            user=cls.member_user,
            membership=cls.membership,
            screenshot=SimpleUploadedFile(
                "proof.png",
                PNG_IMAGE_BYTES,
                content_type="image/png",
            ),
            utr_number="ADMINUTR001",
            payment_status=PaymentStatus.PENDING,
        )

    def setUp(self):
        self.client.force_login(self.staff_user)

    def test_paymentproof_admin_changelist_shows_payment_metadata(self):
        response = self.client.get(
            reverse(f"admin:{PaymentProof._meta.app_label}_{PaymentProof._meta.model_name}_changelist")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "paymentmember")
        self.assertContains(response, "member@example.com")
        self.assertContains(response, "Quarterly")
        self.assertContains(response, "ADMINUTR001")

    def test_paymentproof_admin_bulk_approve_action_activates_membership(self):
        changelist_url = reverse(
            f"admin:{PaymentProof._meta.app_label}_{PaymentProof._meta.model_name}_changelist"
        )
        response = self.client.post(
            changelist_url,
            {
                "action": "approve_selected_payments",
                "_selected_action": [self.payment_proof.pk],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.payment_proof.refresh_from_db()
        self.membership.refresh_from_db()
        self.assertEqual(self.payment_proof.payment_status, PaymentStatus.APPROVED)
        self.assertEqual(self.membership.membership_status, MembershipStatus.ACTIVE)
        self.assertEqual(self.membership.payment_status, PaymentStatus.APPROVED)

    def test_paymentproof_admin_change_form_approve_button_updates_membership(self):
        self.payment_proof.reject(admin_note="Reset to rejected first.")
        self.payment_proof.refresh_from_db()
        self.membership.refresh_from_db()

        change_url = reverse(
            f"admin:{PaymentProof._meta.app_label}_{PaymentProof._meta.model_name}_change",
            args=[self.payment_proof.pk],
        )
        response = self.client.post(
            change_url,
            {
                "payment_status": PaymentStatus.REJECTED,
                "admin_note": "Verified from admin button.",
                "_approve-payment": "Approve Payment",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.payment_proof.refresh_from_db()
        self.membership.refresh_from_db()
        self.assertEqual(self.payment_proof.payment_status, PaymentStatus.APPROVED)
        self.assertEqual(self.payment_proof.admin_note, "Verified from admin button.")
        self.assertEqual(self.membership.membership_status, MembershipStatus.ACTIVE)


class CustomAdminPortalPaymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(
            username="portaladmin",
            password="admin12345",
            email="portaladmin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        cls.member_user = User.objects.create_user(
            username="portalmember",
            password="secret123",
            email="portalmember@example.com",
        )
        cls.membership = Membership.objects.create(
            user=cls.member_user,
            plan_name="Monthly",
            amount="999.00",
            duration=30,
            payment_status=PaymentStatus.PENDING,
            membership_status=MembershipStatus.PENDING,
        )
        cls.payment_proof = PaymentProof.objects.create(
            user=cls.member_user,
            membership=cls.membership,
            screenshot=SimpleUploadedFile(
                "portal-proof.png",
                PNG_IMAGE_BYTES,
                content_type="image/png",
            ),
            utr_number="PORTALUTR001",
            payment_status=PaymentStatus.PENDING,
        )

    def setUp(self):
        self.client.force_login(self.staff_user)

    def test_admin_portal_shows_membership_payment_review_data(self):
        response = self.client.get("/admin_portal")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Membership Payment Review")
        self.assertContains(response, "portalmember")
        self.assertContains(response, "PORTALUTR001")
        self.assertContains(response, "Approve Payment")

    def test_admin_portal_can_approve_membership_payment(self):
        response = self.client.post(
            "/admin_portal",
            {
                "portal_action": "review_membership_payment",
                "payment_id": self.payment_proof.pk,
                "payment_decision": "approve",
                "admin_note": "Approved from custom admin portal.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.payment_proof.refresh_from_db()
        self.membership.refresh_from_db()
        self.assertEqual(self.payment_proof.payment_status, PaymentStatus.APPROVED)
        self.assertEqual(self.payment_proof.admin_note, "Approved from custom admin portal.")
        self.assertEqual(self.membership.payment_status, PaymentStatus.APPROVED)
        self.assertEqual(self.membership.membership_status, MembershipStatus.ACTIVE)

    def test_admin_portal_can_reject_membership_payment(self):
        response = self.client.post(
            "/admin_portal",
            {
                "portal_action": "review_membership_payment",
                "payment_id": self.payment_proof.pk,
                "payment_decision": "reject",
                "admin_note": "Screenshot does not match the paid amount.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.payment_proof.refresh_from_db()
        self.membership.refresh_from_db()
        self.assertEqual(self.payment_proof.payment_status, PaymentStatus.REJECTED)
        self.assertEqual(
            self.payment_proof.admin_note,
            "Screenshot does not match the paid amount.",
        )
        self.assertEqual(self.membership.payment_status, PaymentStatus.REJECTED)
        self.assertEqual(self.membership.membership_status, MembershipStatus.INACTIVE)
