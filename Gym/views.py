from functools import wraps
from io import BytesIO
from urllib.parse import urlencode

import base64
import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from workouts.forms import ExerciseForm
from workouts.models import Exercise


from .forms import (
    ContactForm,
    MemberRegistrationForm,
    PaymentProofForm,
    StaffAuthenticationForm,
    StyledAuthenticationForm,
    StyledPasswordChangeForm,
)
from .models import (
    Address,
    Attendance,
    Gender,
    Gym_split,
    Gym_user,
    Membership,
    MembershipStatus,
    Muscle_strength,
    PaymentProof,
    PaymentStatus,
)

try:
    import qrcode
except ImportError:
    qrcode = None


CITY_OPTIONS = [
    "Kulhan",
    "Sahastradhara Road",
    "Gujrara Mansingh",
    "Jakhan",
    "Rajpur Road",
    "Malsi",
    "Bisht Gaon",
    "Dalanwala",
    "Vasant Vihar",
    "Clement Town",
]

GENDER_OPTIONS = {
    "male": "Male",
    "female": "Female",
}

MUSCLE_STRENGTH_OPTIONS = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
}

GYM_SPLIT_OPTIONS = {
    "5_day_split": "5 Day Split",
    "3_day_split": "3 Day Split (PPL)",
}

MEMBERSHIP_PLANS = {
    "monthly": {
        "slug": "monthly",
        "name": "Monthly",
        "price": "Rs 999",
        "amount": 999,
        "duration": 30,
        "billing_cycle": "Per month",
        "description": "Flexible month-to-month access for members who want to start immediately.",
    },
    "quarterly": {
        "slug": "quarterly",
        "name": "Quarterly",
        "price": "Rs 2,499",
        "amount": 2499,
        "duration": 90,
        "billing_cycle": "Per 3 months",
        "description": "Our most popular choice with better value and more time to build consistency.",
    },
    "yearly": {
        "slug": "yearly",
        "name": "Yearly",
        "price": "Rs 8,999",
        "amount": 8999,
        "duration": 365,
        "billing_cycle": "Per year",
        "description": "The best long-term value for members committed to a full year of progress.",
    },
}


def _is_staff_user(user):
    return user.is_authenticated and user.is_staff


def _requested_next_url(request):
    return (request.GET.get("next") or request.POST.get("next") or "").strip()


def _safe_next_url(request, default_url):
    next_url = _requested_next_url(request)
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return default_url


def _safe_referer_url(request, default_url):
    referer = (request.META.get("HTTP_REFERER") or "").strip()
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return referer
    return default_url


def _login_redirect_url(request, next_url=None):
    target_url = next_url or request.get_full_path()
    return f"{reverse('login')}?{urlencode({'next': target_url})}"


def _admin_login_redirect_url(request, next_url=None):
    target_url = next_url or request.get_full_path()
    return f"{reverse('admin_login')}?{urlencode({'next': target_url})}"


def _get_membership_plan_or_404(plan_slug):
    plan = MEMBERSHIP_PLANS.get((plan_slug or "").lower())
    if not plan:
        raise Http404("Membership plan not found.")
    return plan


def _membership_payment_proof(membership):
    if not membership:
        return None
    try:
        return membership.payment_proof
    except PaymentProof.DoesNotExist:
        return None


def _build_upi_payment_uri(plan):
    upi_id = str(getattr(settings, "UPI_PAYMENT_ID", "gymowner@upi")).strip()
    payee_name = str(getattr(settings, "UPI_PAYEE_NAME", "fitnessZone")).strip()
    note = f"{plan['name']} membership payment"
    query = urlencode(
        {
            "pa": upi_id,
            "pn": payee_name,
            "am": f"{plan['amount']:.2f}",
            "cu": "INR",
            "tn": note,
        }
    )
    return f"upi://pay?{query}"


def _generate_upi_qr_data_uri(payment_uri):
    if qrcode is None:
        return None

    qr = qrcode.QRCode(border=2, box_size=10)
    qr.add_data(payment_uri)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="#0f0f0f", back_color="white")
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")
    encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"


def _get_membership_dashboard_context(auth_user):
    Membership.expire_overdue_memberships()
    if not auth_user:
        return {
            "current_membership": None,
            "active_membership": None,
            "membership_history": [],
            "membership_pending_count": 0,
            "membership_total_count": 0,
        }

    memberships = list(
        Membership.objects.filter(user=auth_user).order_by("-created_at")
    )
    proofs_by_membership_id = {
        proof.membership_id: proof
        for proof in PaymentProof.objects.filter(membership__in=memberships)
    }
    membership_history = [
        {
            "membership": membership,
            "payment_proof": proofs_by_membership_id.get(membership.id),
        }
        for membership in memberships[:10]
    ]
    active_membership = next(
        (membership for membership in memberships if membership.membership_status == MembershipStatus.ACTIVE),
        None,
    )
    current_membership = active_membership or (memberships[0] if memberships else None)

    return {
        "current_membership": current_membership,
        "active_membership": active_membership,
        "membership_history": membership_history,
        "membership_pending_count": sum(
            1
            for membership in memberships
            if membership.payment_status == PaymentStatus.PENDING
        ),
        "membership_total_count": len(memberships),
    }


def member_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = _get_logged_in_user(request)
        if not user:
            if _is_staff_user(request.user):
                return redirect(reverse("admin_portal"))
            return redirect(_login_redirect_url(request))

        request.logged_in_user = user
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def _admin_session_required(request):
    if not _is_staff_user(request.user):
        return redirect(_admin_login_redirect_url(request))
    return None


def _get_logged_in_user(request):
    if not request.user.is_authenticated or request.user.is_staff:
        return None
    return Gym_user.objects.filter(user=request.user).first()


def _member_access_redirect(request):
    if _is_staff_user(request.user):
        return redirect("/all_members")
    if request.user.is_authenticated:
        return redirect("/profile_page")
    return redirect(_login_redirect_url(request))


def _get_member_user_for_page(request, query_param="u_id", fallback_to_session=True):
    current_profile = _get_logged_in_user(request)
    requested_user_id = request.GET.get(query_param)
    if not requested_user_id and fallback_to_session and current_profile:
        requested_user_id = current_profile.id

    if not requested_user_id:
        return None, _member_access_redirect(request)

    try:
        user = Gym_user.objects.get(pk=requested_user_id)
    except (Gym_user.DoesNotExist, TypeError, ValueError):
        return None, _member_access_redirect(request)

    if _is_staff_user(request.user):
        return user, None

    if not current_profile or current_profile.id != user.id:
        return None, _member_access_redirect(request)

    return user, None


def _ensure_registration_reference_data():
    addresses = {
        city: Address.objects.get_or_create(area=city)[0]
        for city in CITY_OPTIONS
    }
    genders = {
        key: Gender.objects.get_or_create(gender=value)[0]
        for key, value in GENDER_OPTIONS.items()
    }
    muscle_strengths = {
        key: Muscle_strength.objects.get_or_create(type=value)[0]
        for key, value in MUSCLE_STRENGTH_OPTIONS.items()
    }
    gym_splits = {
        key: Gym_split.objects.get_or_create(split_name=value)[0]
        for key, value in GYM_SPLIT_OPTIONS.items()
    }
    return addresses, genders, muscle_strengths, gym_splits


def _get_registration_relations(cleaned_data):
    return {
        "address": Address.objects.get(area=cleaned_data["address"]),
        "gender": Gender.objects.get(gender=cleaned_data["gender"]),
        "muscle_strength": Muscle_strength.objects.get(type=cleaned_data["muscle_strength"]),
        "gym_split": Gym_split.objects.get(split_name=cleaned_data["gym_split"]),
    }


def _create_member_profile(user, cleaned_data):
    relations = _get_registration_relations(cleaned_data)
    return Gym_user.objects.create(
        user=user,
        first_name=user.first_name,
        last_name=user.last_name,
        dob=cleaned_data["dob"],
        phone_number=int(cleaned_data["phone_number"]),
        weight=cleaned_data["weight"],
        height=cleaned_data["height"],
        username=user.username,
        password="",
        address=relations["address"],
        gender=relations["gender"],
        gym_split=relations["gym_split"],
        muscle_strength=relations["muscle_strength"],
        email=user.email,
    )


def _build_bmi_context(user):
    bmi = round(user.weight / ((user.height / 100) ** 2), 2)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    return {
        "bmi": bmi,
        "bmi_status": category,
        "today": datetime.datetime.now().strftime("%A"),
    }


def _registration_step_for_form(form):
    step_one_fields = {
        "first_name",
        "last_name",
        "dob",
        "phone_number",
        "height",
        "weight",
    }
    step_two_fields = {
        "gender",
        "muscle_strength",
        "address",
        "gym_split",
        "email",
    }
    step_three_fields = {
        "username",
        "password1",
        "password2",
        "accept_terms",
    }

    error_fields = set(form.errors.keys())
    if form.non_field_errors() or error_fields & step_three_fields:
        return 3
    if error_fields & step_two_fields:
        return 2
    if error_fields & step_one_fields:
        return 1
    return 1


def _contact_notification_email():
    return (
        str(getattr(settings, "CONTACT_NOTIFICATION_EMAIL", "") or "").strip()
        or User.objects.filter(is_staff=True)
        .exclude(email__isnull=True)
        .exclude(email="")
        .values_list("email", flat=True)
        .first()
        or str(getattr(settings, "ADMIN_EMAIL", "") or "").strip()
        or "admin@example.com"
    )


def _push_pending_csrf_message(request):
    csrf_message = request.session.pop("pending_csrf_error_message", "")
    if csrf_message:
        messages.error(request, csrf_message)


def csrf_failure_view(request, reason=""):
    request.session["pending_csrf_error_message"] = (
        "Your form session expired or became outdated. Please try again with the refreshed page."
    )
    fallback_url = request.path or reverse("login")

    return redirect(_safe_referer_url(request, fallback_url))


def home(request):
    return render(request, "home.html")

def membership(request):
    return render(request, "membership.html")


def join_membership(request, plan_slug):
    plan = _get_membership_plan_or_404(plan_slug)
    payment_url = reverse("payment_page", kwargs={"plan_slug": plan["slug"]})

    if _is_staff_user(request.user):
        return redirect(reverse("admin_portal"))

    if _get_logged_in_user(request):
        return redirect(payment_url)

    return redirect(_login_redirect_url(request, payment_url))


@never_cache
@ensure_csrf_cookie
@member_login_required
def payment_page(request, plan_slug):
    _push_pending_csrf_message(request)
    plan = _get_membership_plan_or_404(plan_slug)
    member_profile = request.logged_in_user
    pending_membership = Membership.objects.filter(
        user=request.user,
        plan_name=plan["name"],
        payment_status=PaymentStatus.PENDING,
    ).order_by("-created_at").first()
    latest_membership_for_plan = Membership.objects.filter(
        user=request.user,
        plan_name=plan["name"],
    ).order_by("-created_at").first()

    if request.method == "POST":
        if pending_membership:
            messages.warning(
                request,
                "You already have a payment awaiting verification for this membership plan.",
            )
            return redirect("payment_page", plan_slug=plan["slug"])

        form = PaymentProofForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                membership = Membership.objects.create(
                    user=request.user,
                    plan_name=plan["name"],
                    amount=plan["amount"],
                    duration=plan["duration"],
                    payment_status=PaymentStatus.PENDING,
                    membership_status=MembershipStatus.PENDING,
                )
                payment_proof = form.save(commit=False)
                payment_proof.user = request.user
                payment_proof.membership = membership
                payment_proof.save()

            messages.success(
                request,
                "Payment submitted successfully. Waiting for admin verification.",
            )
            return redirect("payment_page", plan_slug=plan["slug"])

        messages.error(
            request,
            "Please correct the payment form errors and submit your proof again.",
        )
    else:
        form = PaymentProofForm()

    dashboard_context = _get_membership_dashboard_context(request.user)
    payment_uri = _build_upi_payment_uri(plan)
    return render(
        request,
        "payment.html",
        {
            "plan": plan,
            "user": member_profile,
            "payment_form": form,
            "payment_uri": payment_uri,
            "upi_id": getattr(settings, "UPI_PAYMENT_ID", "gymowner@upi"),
            "upi_payee_name": getattr(settings, "UPI_PAYEE_NAME", "fitnessZone"),
            "payment_qr_data_uri": _generate_upi_qr_data_uri(payment_uri),
            "pending_membership": pending_membership,
            "latest_plan_membership": latest_membership_for_plan,
            **dashboard_context,
        },
    )

@never_cache
@ensure_csrf_cookie
def contact_view(request):
    _push_pending_csrf_message(request)
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            recipient_email = _contact_notification_email()

            try:
                send_mail(
                    subject=f"New contact message: {contact.subject}",
                    message=(
                        "A new contact form submission was received.\n\n"
                        f"Name: {contact.name}\n"
                        f"Email: {contact.email}\n"
                        f"Subject: {contact.subject}\n\n"
                        "Message:\n"
                        f"{contact.message}"
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@fitnesspro.com"),
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
            except Exception:
                messages.warning(
                    request,
                    "Your message was saved, but the admin email notification could not be delivered right now.",
                )

            messages.success(
                request,
                "Thank you for contacting FitnessPro. Your message has been sent successfully.",
            )
            return redirect("contact")

        messages.error(request, "Please correct the errors below and submit the form again.")
    else:
        form = ContactForm()

    return render(request, "contact.html", {"form": form})


contact_us = contact_view

@never_cache
@ensure_csrf_cookie
def register_view(request):
    _push_pending_csrf_message(request)
    _ensure_registration_reference_data()
    next_url = _requested_next_url(request)
    is_admin_creator = _is_staff_user(request.user)

    if request.user.is_authenticated and not is_admin_creator:
        return redirect(_safe_next_url(request, reverse("profile_page")))

    if request.method == "POST":
        form = MemberRegistrationForm(
            request.POST,
            is_admin_creator=is_admin_creator,
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    auth_user = form.save()
                    profile = _create_member_profile(auth_user, form.cleaned_data)
            except IntegrityError:
                form.add_error(
                    "username",
                    "We couldn't create this member account right now. Please try a different username.",
                )
            else:
                if is_admin_creator:
                    messages.success(
                        request,
                        f"{profile.first_name} {profile.last_name} was registered successfully.",
                    )
                    return redirect("new_registration")

                authenticated_user = authenticate(
                    request,
                    username=auth_user.username,
                    password=form.cleaned_data["password1"],
                )
                if authenticated_user is not None:
                    auth_login(request, authenticated_user)
                return redirect(_safe_next_url(request, reverse("profile_page")))

        if form.errors:
            form.apply_error_styles()
            messages.error(request, "Please correct the highlighted fields and try again.")
    else:
        form = MemberRegistrationForm(is_admin_creator=is_admin_creator)

    return render(
        request,
        "new_registration.html",
        {
            "form": form,
            "next_url": next_url,
            "is_admin_creator": is_admin_creator,
            "initial_step": _registration_step_for_form(form),
        },
    )


@never_cache
@ensure_csrf_cookie
def login_view(request):
    _push_pending_csrf_message(request)
    next_url = _requested_next_url(request)

    if request.user.is_authenticated:
        default_redirect = reverse("admin_portal") if _is_staff_user(request.user) else reverse("profile_page")
        return redirect(_safe_next_url(request, default_redirect))

    if request.method == "POST":
        form = StyledAuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user is not None:
                auth_login(request, authenticated_user)
                default_redirect = reverse("admin_portal") if authenticated_user.is_staff else reverse("profile_page")
                return redirect(_safe_next_url(request, default_redirect))
    else:
        form = StyledAuthenticationForm(request=request)

    return render(
        request,
        "login_page.html",
        {
            "form": form,
            "next_url": next_url,
        },
    )


@never_cache
@ensure_csrf_cookie
def all_members(request):
    admin_redirect = _admin_session_required(request)
    if admin_redirect:
        return admin_redirect

    _push_pending_csrf_message(request)
    members = Gym_user.get_all_users()
    all_users_data = {'users': members}
    return render(request, 'all_members.html', all_users_data)

@never_cache
@ensure_csrf_cookie
def attendance(request):
    admin_redirect = _admin_session_required(request)
    if admin_redirect:
        return admin_redirect

    _push_pending_csrf_message(request)
    today = datetime.datetime.now().date()
    
    if request.method == "GET":
        members = Gym_user.objects.select_related('address', 'gender', 'gym_split', 'muscle_strength').order_by('first_name')
        attendance_records = Attendance.objects.filter(date=today).values_list('member_id', 'status')
        attendance_dict = dict(attendance_records)
        
        members_with_attendance = [
            {
                'member': member,
                'status': attendance_dict.get(member.id, 'absent')
            }
            for member in members
        ]
        
        return render(request, 'attendance.html', {
            'members': members_with_attendance,
            'today': today
        })

    if request.method == "POST":
        attendance_data = request.POST.getlist('attendance')
        errors = []
        updated_count = 0
        
        for entry in attendance_data:
            if not entry:
                continue
                
            parts = entry.split(':')
            if len(parts) != 2:
                continue
                
            member_id, status = parts
            if status not in ['present', 'absent']:
                errors.append(f"Invalid status for member {member_id}.")
                continue
            
            try:
                member = Gym_user.objects.get(id=int(member_id))
                attendance_obj, created = Attendance.objects.update_or_create(
                    member=member,
                    date=today,
                    defaults={'status': status}
                )
                
                if status == 'present' and created:
                    member.no_of_days += 1
                    member.save(update_fields=['no_of_days'])
                    
                updated_count += 1
            except (Gym_user.DoesNotExist, ValueError):
                errors.append(f"Invalid member ID: {member_id}")
        
        members = Gym_user.objects.select_related('address', 'gender', 'gym_split', 'muscle_strength').order_by('first_name')
        attendance_records = Attendance.objects.filter(date=today).values_list('member_id', 'status')
        attendance_dict = dict(attendance_records)
        
        members_with_attendance = [
            {
                'member': member,
                'status': attendance_dict.get(member.id, 'absent')
            }
            for member in members
        ]
        
        data = {
            'members': members_with_attendance,
            'today': today
        }
        
        if updated_count > 0:
            data['msg'] = f"Attendance updated for {updated_count} member(s)."
        if errors:
            data['error'] = " ".join(errors)
        if updated_count == 0 and not errors:
            data['error'] = "No attendance records to update."
        
        return render(request, 'attendance.html', data)



def admin_portal(request):
    admin_redirect = _admin_session_required(request)
    if admin_redirect:
        return admin_redirect

    Membership.expire_overdue_memberships()

    if request.method == "POST" and request.POST.get("portal_action") == "review_membership_payment":
        proof_id = request.POST.get("payment_id")
        payment_decision = request.POST.get("payment_decision")

        if not proof_id:
            messages.error(request, "The selected membership payment could not be found.")
            return redirect("admin_portal")

        payment_proof = (
            PaymentProof.objects.select_related("membership", "user")
            .filter(pk=proof_id)
            .first()
        )
        if not payment_proof:
            messages.error(request, "The selected membership payment no longer exists.")
            return redirect("admin_portal")

        # Reuse the centralized model methods so the custom portal and Django admin
        # always apply the same approval, rejection, and activation workflow.
        admin_note = request.POST.get("admin_note", "").strip() or payment_proof.admin_note or None
        if payment_decision == "approve":
            payment_proof.approve(admin_note=admin_note)
            messages.success(
                request,
                f"Payment for {payment_proof.user.username}'s {payment_proof.membership.plan_name} plan was approved successfully.",
            )
        elif payment_decision == "reject":
            payment_proof.reject(admin_note=admin_note)
            messages.warning(
                request,
                f"Payment for {payment_proof.user.username}'s {payment_proof.membership.plan_name} plan was rejected.",
            )
        else:
            messages.error(request, "Please choose a valid membership payment action.")

        return redirect("admin_portal")

    current_timestamp = timezone.localtime()
    today = current_timestamp.date()
    current_month_start = today.replace(day=1)
    
    # Total members count
    total_members = Gym_user.objects.count()
    
    # New members this month
    monthly_members = Gym_user.objects.filter(
        date_of_joining__month=current_timestamp.month,
        date_of_joining__year=current_timestamp.year,
    ).count()
    
    # Members present today
    present_today = Attendance.objects.filter(
        date=today,
        status='present'
    ).count()
    
    # Members absent today
    absent_today = Attendance.objects.filter(
        date=today,
        status='absent'
    ).count()
    
    # Total staff/trainers
    total_staff = User.objects.filter(is_staff=True).count()
    
    # Calculate growth rate (percentage change from last month)
    last_month_date = current_month_start - datetime.timedelta(days=1)
    last_month_start = last_month_date.replace(day=1)
    last_month_members = Gym_user.objects.filter(
        date_of_joining__date__gte=last_month_start,
        date_of_joining__date__lt=current_month_start,
    ).count()
    
    growth_rate = 0
    if last_month_members > 0:
        growth_rate = round(((monthly_members - last_month_members) / last_month_members) * 100, 1)
    
    # Active members (joined at least once this month or have attended)
    active_members = Gym_user.objects.filter(
        date_of_joining__date__lte=today
    ).exclude(
        attendance_records__date__isnull=True
    ).distinct().count() if Attendance.objects.exists() else 0

    membership_payments = PaymentProof.objects.select_related("user", "membership")
    pending_membership_payments = list(
        membership_payments.filter(payment_status=PaymentStatus.PENDING)[:6]
    )
    recent_membership_payments = list(membership_payments[:10])
    exercise_context = Exercise.library_context(request.GET.get("exercise_group"))

    return render(
        request,
        "admin_portal.html",
        {
            "admin": request.user,
            "total_members": total_members,
            "monthly_members": monthly_members,
            "present_today": present_today,
            "absent_today": absent_today,
            "total_staff": total_staff,
            "growth_rate": growth_rate,
            "active_members": active_members,
            "pending_payment_count": membership_payments.filter(
                payment_status=PaymentStatus.PENDING
            ).count(),
            "approved_payment_count": membership_payments.filter(
                payment_status=PaymentStatus.APPROVED
            ).count(),
            "rejected_payment_count": membership_payments.filter(
                payment_status=PaymentStatus.REJECTED
            ).count(),
            "active_membership_count": Membership.objects.filter(
                membership_status=MembershipStatus.ACTIVE
            ).count(),
            "pending_membership_payments": pending_membership_payments,
            "recent_membership_payments": recent_membership_payments,
            "payment_admin_url": reverse(
                f"admin:{PaymentProof._meta.app_label}_{PaymentProof._meta.model_name}_changelist"
            ),
            "exercise_count": Exercise.objects.count(),
            "exercise_group_count": len(exercise_context["muscle_group_filters"]),
            "exercise_admin_add_url": reverse("add_exercise"),
            "exercise_admin_changelist_url": reverse(
                f"admin:{Exercise._meta.app_label}_{Exercise._meta.model_name}_changelist"
            ),
            "today": today,
            **exercise_context,
        },
    )


@never_cache
@ensure_csrf_cookie
def add_exercise(request, exercise_id=None):
    admin_redirect = _admin_session_required(request)
    if admin_redirect:
        return admin_redirect

    _push_pending_csrf_message(request)

    exercise = get_object_or_404(Exercise, pk=exercise_id) if exercise_id else None

    if request.method == "POST":
        form = ExerciseForm(request.POST, request.FILES, instance=exercise)
        if form.is_valid():
            saved_exercise = form.save()
            submit_action = request.POST.get("submit_action", "save")
            messages.success(
                request,
                f"{saved_exercise.name} was {'updated' if exercise else 'added'} successfully.",
            )
            if submit_action == "save_add_another":
                return redirect("add_exercise")
            if submit_action == "save_continue":
                return redirect("edit_exercise", exercise_id=saved_exercise.id)
            return redirect("admin_portal")
        messages.error(request, "Please fix the exercise form errors below.")
    else:
        form = ExerciseForm(instance=exercise)

    preview_image_url = ""
    if exercise and exercise.image:
        preview_image_url = exercise.image.url
    elif exercise and exercise.image_url:
        preview_image_url = exercise.image_url

    return render(
        request,
        "add_exercise.html",
        {
            "form": form,
            "exercise": exercise,
            "exercise_count": Exercise.objects.count(),
            "is_editing": exercise is not None,
            "preview_image_url": preview_image_url,
        },
    )


@never_cache
@ensure_csrf_cookie
def change_admin_password(request):
    admin_redirect = _admin_session_required(request)
    if admin_redirect:
        return admin_redirect

    _push_pending_csrf_message(request)

    if request.method == "POST":
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            updated_user = form.save()
            update_session_auth_hash(request, updated_user)
            messages.success(request, "Your admin password has been updated successfully.")
            return redirect("change_admin_password")
        messages.error(request, "Please fix the password errors below.")
    else:
        form = StyledPasswordChangeForm(request.user)

    return render(
        request,
        "change_admin_password.html",
        {
            "form": form,
        },
    )


@never_cache
@ensure_csrf_cookie
def change_user_password(request):
    member_profile = _get_logged_in_user(request)
    if not member_profile:
        return redirect(_login_redirect_url(request, reverse("change_user_password")))

    _push_pending_csrf_message(request)

    if request.method == "POST":
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            updated_user = form.save()
            update_session_auth_hash(request, updated_user)
            messages.success(request, "Your password has been updated successfully.")
            return redirect("change_user_password")
        messages.error(request, "Please fix the password errors below.")
    else:
        form = StyledPasswordChangeForm(request.user)

    return render(
        request,
        "change_user_password.html",
        {
            "form": form,
            "member_profile": member_profile,
        },
    )


@never_cache
@ensure_csrf_cookie
def admin_login_view(request):
    _push_pending_csrf_message(request)
    next_url = _requested_next_url(request)
    if _is_staff_user(request.user):
        return redirect(_safe_next_url(request, reverse("admin_portal")))

    if request.method == "POST":
        form = StaffAuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user is not None and authenticated_user.is_staff:
                auth_login(request, authenticated_user)
                return redirect(_safe_next_url(request, reverse("admin_portal")))
    else:
        form = StaffAuthenticationForm(request=request)

    return render(
        request,
        "admin_login.html",
        {
            "form": form,
            "next_url": next_url,
        },
    )


def admin_logout_view(request):
    auth_logout(request)
    return redirect("admin_login")


def logout_view(request):
    auth_logout(request)
    return redirect("/")


def delete_user(request):
    admin_redirect = _admin_session_required(request)
    if admin_redirect:
        return admin_redirect

    user_id = request.GET.get("u_id")
    user_ = Gym_user.objects.get(id=user_id)
    if user_.user_id:
        user_.user.delete()
    else:
        user_.delete()
    return redirect("/all_members")


def delete_profbyuser(request):
    user_id = request.GET.get("u_id")
    member_profile = _get_logged_in_user(request)
    if not member_profile and not _is_staff_user(request.user):
        return redirect("/login")

    if not _is_staff_user(request.user) and str(member_profile.id) != str(user_id):
        return redirect("/login")

    user_ = Gym_user.objects.get(id=user_id)
    if user_.user_id:
        is_self_delete = request.user.is_authenticated and request.user.id == user_.user_id
        if is_self_delete:
            auth_logout(request)
        user_.user.delete()
    else:
        user_.delete()
    return redirect("/")



@require_POST
def upload_profile_image(request):
    try:
        user_id = request.POST.get('user_id') or request.GET.get('u_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'User ID is required.'})

        logged_in_member = _get_logged_in_user(request)
        is_allowed = _is_staff_user(request.user) or (
            logged_in_member and str(logged_in_member.id) == str(user_id)
        )
        if not is_allowed:
            return JsonResponse(
                {'success': False, 'message': 'You are not authorized to update this profile.'},
                status=403,
            )

        user = Gym_user.objects.get(id=int(user_id))
        
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return JsonResponse({'success': False, 'message': 'Invalid file type. Please upload JPEG, PNG, GIF, or WebP images.'})
            
            if image_file.size > 5 * 1024 * 1024:
                return JsonResponse({'success': False, 'message': 'File too large. Please upload images smaller than 5MB.'})
            
            if user.image and user.image.name != "users_profile_images/image.png":
                try:
                    user.image.delete(save=False)
                except:
                    pass
            
            user.image.save(image_file.name, image_file, save=True)
            
            return JsonResponse({
                'success': True, 
                'message': 'Profile picture updated successfully!',
                'image_url': user.image.url
            })
        else:
            return JsonResponse({'success': False, 'message': 'No image file provided.'})
            
    except Gym_user.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User does not exist.'})
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid user ID format.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})


def diet_plan(request):
    user, redirect_response = _get_member_user_for_page(request, query_param="pid")
    if redirect_response:
        return redirect_response

    return render(request, 'diet_plan.html', {'user': user})


def workout_plan(request):
    user, redirect_response = _get_member_user_for_page(request, query_param="pid")
    if redirect_response:
        return redirect_response

    data = {'user': user}
    today = datetime.datetime.now()
    data['today'] = today.strftime("%A")
    return render(request, 'workout_plan.html', data)


def workout(request):
    user, redirect_response = _get_member_user_for_page(request, query_param="pid")
    if redirect_response:
        return redirect_response

    data = {'user': user}
    today_ = datetime.datetime.now()
    data['today'] = today_.strftime("%A")
    split_name = user.gym_split.split_name.lower()
    days_since_joining = max((today_.date() - user.date_of_joining.date()).days, 0)

    if split_name.startswith("5"):
        exercise_cycle = ["chest", "back", "shoulder", "bicep_tricep", "leg", "rest"]
    else:
        exercise_cycle = ["push", "pull", "leg"]

    data['exercise'] = exercise_cycle[days_since_joining % len(exercise_cycle)]

    return render(request, 'workout.html', data)


def userdetails(request):
    admin_redirect = _admin_session_required(request)
    if admin_redirect:
        return admin_redirect

    _id_ = request.GET.get("u_id")
    singleuser = Gym_user.get_user_by_id(int(_id_))
    user_data = {"a_user": singleuser}
    user_data.update(_build_bmi_context(singleuser))
    user_data["member_since"] = singleuser.date_of_joining
    user_data["account_status"] = "Active"
    user_data["last_login_display"] = (
        singleuser.user.last_login if singleuser.user and singleuser.user.last_login else "No login activity recorded yet."
    )

    return render(request, 'userdetails.html', user_data)

def profilePage(request):
    singleuser, redirect_response = _get_member_user_for_page(request)
    if redirect_response:
        return redirect_response

    user_data = {"user": singleuser}
    user_data.update(_build_bmi_context(singleuser))
    user_data.update(_get_membership_dashboard_context(singleuser.user))
    return render(request, 'profile_page.html', user_data)


def searchPage(request):
    admin_redirect = _admin_session_required(request)
    if admin_redirect:
        return admin_redirect

    if request.method != "POST":
        return redirect('/all_members')

    query = (request.POST.get("searchedMember") or "").strip()
    searchedMember = Gym_user.get_searched_members(query)
    if not searchedMember:
        searchedMember = Gym_user.by_lastName(query)
        if not searchedMember:
            searchedMember = Gym_user.by_id(query)
            if not searchedMember:
                searchedMember = Gym_user.by_username(query)
                if not searchedMember:
                    searchedMember = Gym_user.by_dob(query)
    data = {"members": searchedMember, "query": query}
    return render(request, 'searchPage.html', data)


# Backward-compatible view aliases
new_registration = register_view
login = login_view
logout = logout_view
admin_login = admin_login_view
admin_logout = admin_logout_view
