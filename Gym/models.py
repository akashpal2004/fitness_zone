from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone

# Create your models here.

class Gym_split(models.Model):
    
    split_name = models.CharField(max_length=500)
    
    def __str__(self):
        return self.split_name




class Gender(models.Model):
    
    gender = models.CharField(max_length=30)
    
    def __str__(self):
        return self.gender




class Muscle_strength(models.Model):
    
    type = models.CharField(max_length=20)
    
    def __str__(self):
        return self.type




class Address(models.Model):

    area = models.CharField(max_length=30)
    
    def __str__(self):
        return self.area
    



class Gym_user(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="gym_profile",
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=50)
    last_name  = models.CharField(max_length=50)
    no_of_days = models.IntegerField(default=0)
    dob = models.DateField()
    phone_number = models.IntegerField()
    image = models.ImageField(upload_to="users_profile_images/", default="users_profile_images/image.png")
    weight = models.IntegerField()
    height = models.IntegerField()
    date_of_joining = models.DateTimeField(auto_now_add=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=100, blank=True, default="", editable=False)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE)
    gym_split = models.ForeignKey(Gym_split, on_delete=models.CASCADE)
    muscle_strength = models.ForeignKey(Muscle_strength, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.user_id:
            self.username = self.user.username
            if self.user.email:
                self.email = self.user.email
            if self.user.first_name:
                self.first_name = self.user.first_name
            if self.user.last_name:
                self.last_name = self.user.last_name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.first_name +" "+ self.last_name
    
    @staticmethod
    def get_all_users():
        return Gym_user.objects.all()
    
    @staticmethod
    def get_user_by_id(user_id):
        return Gym_user.objects.get(id=user_id)
    
    @staticmethod
    def get_searched_members(query):
        if not query:
            return Gym_user.objects.none()
        return Gym_user.objects.filter(first_name__icontains=query)
    @staticmethod
    def by_lastName(query):
        if not query:
            return Gym_user.objects.none()
        return Gym_user.objects.filter(last_name__icontains=query)
    @staticmethod
    def by_username(query):
        if not query:
            return Gym_user.objects.none()
        return Gym_user.objects.filter(username__icontains=query)
    @staticmethod
    def by_id(query):
        try:
            return Gym_user.objects.filter(id=int(query))
        except (TypeError, ValueError):
            return Gym_user.objects.none()
    @staticmethod
    def by_dob(query):
        if not query:
            return Gym_user.objects.none()
        return Gym_user.objects.filter(dob__contains=query)
    
class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.subject}"


class Attendance(models.Model):
    ATTENDANCE_STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    
    member = models.ForeignKey(Gym_user, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS_CHOICES, default='present')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('member', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'member']),
            models.Index(fields=['member', 'date']),
        ]

    def __str__(self):
        return f"{self.member} - {self.date} ({self.status})"


def payment_proof_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return (
        f"payment_proofs/user_{instance.user_id}/"
        f"membership_{instance.membership_id}/{timestamp}_{uuid4().hex}.{extension}"
    )


def validate_payment_screenshot_size(image_file):
    max_file_size = 5 * 1024 * 1024
    if image_file and image_file.size > max_file_size:
        raise ValidationError("Payment screenshot must be 5 MB or smaller.")


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class MembershipStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    EXPIRED = "expired", "Expired"


class Membership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    plan_name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Membership duration in days.",
    )
    start_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    membership_status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["payment_status", "membership_status"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.plan_name}"

    @property
    def payment_status_badge_class(self):
        return {
            PaymentStatus.PENDING: "status-pending",
            PaymentStatus.APPROVED: "status-approved",
            PaymentStatus.REJECTED: "status-rejected",
        }.get(self.payment_status, "status-neutral")

    @property
    def membership_status_badge_class(self):
        return {
            MembershipStatus.PENDING: "status-pending",
            MembershipStatus.ACTIVE: "status-approved",
            MembershipStatus.INACTIVE: "status-rejected",
            MembershipStatus.EXPIRED: "status-expired",
        }.get(self.membership_status, "status-neutral")

    @property
    def is_currently_active(self):
        self.expire_if_needed(save=True)
        return self.membership_status == MembershipStatus.ACTIVE

    def activate(self, activated_on=None, save=True):
        activation_date = activated_on or timezone.localdate()
        self.start_date = activation_date
        self.expiry_date = activation_date + timedelta(days=self.duration)
        self.payment_status = PaymentStatus.APPROVED
        self.membership_status = MembershipStatus.ACTIVE
        if save:
            self.save(
                update_fields=[
                    "start_date",
                    "expiry_date",
                    "payment_status",
                    "membership_status",
                ]
            )
        return self

    def mark_rejected(self, save=True):
        self.start_date = None
        self.expiry_date = None
        self.payment_status = PaymentStatus.REJECTED
        self.membership_status = MembershipStatus.INACTIVE
        if save:
            self.save(
                update_fields=[
                    "start_date",
                    "expiry_date",
                    "payment_status",
                    "membership_status",
                ]
            )
        return self

    def expire_if_needed(self, today=None, save=False):
        current_day = today or timezone.localdate()
        if (
            self.membership_status == MembershipStatus.ACTIVE
            and self.expiry_date
            and self.expiry_date < current_day
        ):
            self.membership_status = MembershipStatus.EXPIRED
            if save:
                self.save(update_fields=["membership_status"])
            return True
        return False

    @classmethod
    def expire_overdue_memberships(cls, today=None):
        current_day = today or timezone.localdate()
        return cls.objects.filter(
            membership_status=MembershipStatus.ACTIVE,
            expiry_date__lt=current_day,
        ).update(membership_status=MembershipStatus.EXPIRED)


class PaymentMethod(models.TextChoices):
    UPI = "upi", "Manual UPI"


class PaymentProof(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_proofs",
    )
    membership = models.OneToOneField(
        Membership,
        on_delete=models.CASCADE,
        related_name="payment_proof",
    )
    screenshot = models.ImageField(
        upload_to=payment_proof_upload_path,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_payment_screenshot_size,
        ],
    )
    utr_number = models.CharField(max_length=50, unique=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.UPI,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    admin_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["payment_status", "uploaded_at"]),
            models.Index(fields=["user", "uploaded_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.membership.plan_name} - {self.get_payment_status_display()}"

    @property
    def payment_status_badge_class(self):
        return {
            PaymentStatus.PENDING: "status-pending",
            PaymentStatus.APPROVED: "status-approved",
            PaymentStatus.REJECTED: "status-rejected",
        }.get(self.payment_status, "status-neutral")

    def clean(self):
        errors = {}
        if not self.screenshot:
            errors["screenshot"] = "Please upload the payment screenshot."
        if not self.utr_number:
            errors["utr_number"] = "Please enter the UTR / transaction ID."
        if self.membership_id and self.user_id and self.membership.user_id != self.user_id:
            errors["user"] = "Payment proof user must match the membership owner."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = (
                type(self).objects.filter(pk=self.pk).values_list("payment_status", flat=True).first()
            )

        if self.membership_id and self.user_id != self.membership.user_id:
            self.user = self.membership.user

        super().save(*args, **kwargs)

        if previous_status == self.payment_status:
            return

        if self.payment_status == PaymentStatus.APPROVED:
            self.membership.activate()
        elif self.payment_status == PaymentStatus.REJECTED:
            self.membership.mark_rejected()

    def approve(self, admin_note=None):
        if admin_note is not None:
            self.admin_note = admin_note
        self.payment_status = PaymentStatus.APPROVED
        self.save(update_fields=["payment_status", "admin_note"])
        return self

    def reject(self, admin_note=None):
        if admin_note is not None:
            self.admin_note = admin_note
        self.payment_status = PaymentStatus.REJECTED
        self.save(update_fields=["payment_status", "admin_note"])
        return self
