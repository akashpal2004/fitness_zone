import re
from datetime import date

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from .models import Address, Contact, Gender, Gym_split, Gym_user, Muscle_strength, PaymentProof


URL_PATTERN = re.compile(r"(https?://|www\.)", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\D+")
UTR_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,50}$")


class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "username",
                "placeholder": "Username",
                "autocomplete": "username",
            }
        )
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "id": "password",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )


class StaffAuthenticationForm(StyledAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError(
                "This account does not have administrator access.",
                code="not_staff",
            )


class MemberRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "firstname",
                "placeholder": "Enter your first name",
            }
        ),
    )
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "lastname",
                "placeholder": "Enter your last name",
            }
        ),
    )
    dob = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "id": "dob",
                "type": "date",
            }
        )
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "phone",
                "placeholder": "9876543210",
                "inputmode": "numeric",
            }
        ),
    )
    height = forms.IntegerField(
        min_value=100,
        max_value=250,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "height",
                "placeholder": "170",
                "min": 100,
                "max": 250,
            }
        ),
    )
    weight = forms.IntegerField(
        min_value=30,
        max_value=200,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "weight",
                "placeholder": "70",
                "min": 30,
                "max": 200,
            }
        ),
    )
    gender = forms.ChoiceField(
        widget=forms.Select(
            attrs={
                "class": "form-control custom-select",
                "id": "gender",
            }
        )
    )
    muscle_strength = forms.ChoiceField(
        widget=forms.Select(
            attrs={
                "class": "form-control custom-select",
                "id": "muscle_strength",
            }
        )
    )
    address = forms.ChoiceField(
        widget=forms.Select(
            attrs={
                "class": "form-control custom-select",
                "id": "address",
            }
        )
    )
    gym_split = forms.ChoiceField(
        widget=forms.Select(
            attrs={
                "class": "form-control custom-select",
                "id": "gym_split",
            }
        )
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "id": "email",
                "placeholder": "your@email.com",
                "autocomplete": "email",
            }
        )
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "username",
                "placeholder": "Choose a unique username",
                "autocomplete": "username",
            }
        ),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "id": "password",
                "placeholder": "Create a strong password",
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "id": "c_password",
                "placeholder": "Confirm your password",
                "autocomplete": "new-password",
            }
        ),
    )
    accept_terms = forms.BooleanField(
        label="Terms & Conditions",
        required=True,
        error_messages={
            "required": "Please accept the Terms & Conditions and Privacy Policy.",
        },
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "terms",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "first_name",
            "last_name",
            "dob",
            "phone_number",
            "height",
            "weight",
            "gender",
            "muscle_strength",
            "address",
            "gym_split",
            "email",
            "username",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        is_admin_creator = kwargs.pop("is_admin_creator", False)
        super().__init__(*args, **kwargs)
        self.is_admin_creator = is_admin_creator
        self.fields["address"].choices = [("", "Select City")] + [
            (area.area, area.area) for area in Address.objects.order_by("area")
        ]
        self.fields["gender"].choices = [("", "Select Gender")] + [
            (gender.gender, gender.gender) for gender in Gender.objects.order_by("gender")
        ]
        self.fields["muscle_strength"].choices = [("", "Select Level")] + [
            (strength.type, strength.type)
            for strength in Muscle_strength.objects.order_by("type")
        ]
        self.fields["gym_split"].choices = [("", "Select Plan")] + [
            (split.split_name, split.split_name) for split in Gym_split.objects.order_by("split_name")
        ]
        self.fields["password1"].help_text = ""
        self.fields["password2"].help_text = ""
        if is_admin_creator:
            self.fields["accept_terms"].required = False
            self.fields["accept_terms"].widget = forms.HiddenInput(
                attrs={"id": "terms"}
            )

    def apply_error_styles(self):
        for name, field in self.fields.items():
            css_classes = (field.widget.attrs.get("class") or "").replace(" is-invalid", "")
            if self.errors.get(name):
                field.widget.attrs["class"] = f"{css_classes} is-invalid".strip()
                field.widget.attrs["aria-invalid"] = "true"
            else:
                field.widget.attrs["class"] = css_classes.strip()
                field.widget.attrs.pop("aria-invalid", None)

    def clean_first_name(self):
        value = " ".join((self.cleaned_data.get("first_name") or "").split())
        if not re.match(r'^[a-zA-Z\s]+$', value):
            raise ValidationError("First name can only contain alphabets and spaces.")
        if len(value) < 2:
            raise ValidationError("First name must be at least 2 characters long.")
        return value

    def clean_last_name(self):
        value = " ".join((self.cleaned_data.get("last_name") or "").split())
        if not re.match(r'^[a-zA-Z\s]+$', value):
            raise ValidationError("Last name can only contain alphabets and spaces.")
        if len(value) < 2:
            raise ValidationError("Last name must be at least 2 characters long.")
        return value

    def clean_phone_number(self):
        phone_number = PHONE_PATTERN.sub("", self.cleaned_data.get("phone_number") or "")
        if len(phone_number) < 10 or len(phone_number) > 15:
            raise ValidationError("Enter a valid phone number.")
        return phone_number

    def clean_dob(self):
        dob = self.cleaned_data["dob"]
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 13 or age > 100:
            raise ValidationError("Age must be between 13 and 100 years.")
        return dob

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        if Gym_user.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already linked to another member profile.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_attrs = {
            "old_password": {
                "class": "form-control",
                "id": "old_password",
                "placeholder": "Enter your current password",
                "autocomplete": "current-password",
            },
            "new_password1": {
                "class": "form-control",
                "id": "new_password1",
                "placeholder": "Enter your new password",
                "autocomplete": "new-password",
            },
            "new_password2": {
                "class": "form-control",
                "id": "new_password2",
                "placeholder": "Confirm your new password",
                "autocomplete": "new-password",
            },
        }
        for name, attrs in field_attrs.items():
            self.fields[name].widget.attrs.update(attrs)
            self.fields[name].help_text = ""


class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Contact
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your full name",
                    "maxlength": 100,
                    "autocomplete": "name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your email address",
                    "maxlength": 254,
                    "autocomplete": "email",
                }
            ),
            "subject": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "What would you like help with?",
                    "maxlength": 150,
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control message-box",
                    "placeholder": "Tell us how we can help you...",
                    "rows": 6,
                }
            ),
        }

    def clean_name(self):
        name = " ".join((self.cleaned_data.get("name") or "").split())
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        if any(char.isdigit() for char in name):
            raise forms.ValidationError("Name cannot contain numbers.")
        return name

    def clean_subject(self):
        subject = " ".join((self.cleaned_data.get("subject") or "").split())
        if len(subject) < 3:
            raise forms.ValidationError("Subject must be at least 3 characters long.")
        return subject

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long.")
        if len(URL_PATTERN.findall(message)) > 2:
            raise forms.ValidationError("Please remove excessive links from your message.")
        return message

    def clean_website(self):
        website = (self.cleaned_data.get("website") or "").strip()
        if website:
            raise forms.ValidationError("Spam detected.")
        return website


class PaymentProofForm(forms.ModelForm):
    class Meta:
        model = PaymentProof
        fields = ["screenshot", "utr_number"]
        widgets = {
            "screenshot": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/png,image/jpeg,image/webp",
                }
            ),
            "utr_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your UTR / transaction ID",
                    "maxlength": 50,
                    "autocomplete": "off",
                }
            ),
        }

    def clean_utr_number(self):
        utr_number = "".join((self.cleaned_data.get("utr_number") or "").split()).upper()
        if not utr_number:
            raise forms.ValidationError("UTR / transaction ID is required.")
        if not UTR_PATTERN.match(utr_number):
            raise forms.ValidationError("Enter a valid UTR / transaction ID.")

        existing_proof = PaymentProof.objects.filter(utr_number__iexact=utr_number)
        if self.instance.pk:
            existing_proof = existing_proof.exclude(pk=self.instance.pk)
        if existing_proof.exists():
            raise forms.ValidationError("This UTR / transaction ID has already been submitted.")
        return utr_number

    def clean_screenshot(self):
        screenshot = self.cleaned_data.get("screenshot")
        if not screenshot:
            raise forms.ValidationError("Payment screenshot is required.")

        allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
        if getattr(screenshot, "content_type", "") not in allowed_types:
            raise forms.ValidationError("Upload a JPG, PNG, or WebP image.")

        try:
            screenshot.seek(0)
            image = Image.open(screenshot)
            image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            raise forms.ValidationError("The uploaded file is not a valid image.")
        finally:
            screenshot.seek(0)

        return screenshot
