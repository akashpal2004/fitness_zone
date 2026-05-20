from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.utils.html import format_html

from .models import (
    Address,
    Attendance,
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


STATUS_BADGE_STYLES = {
    PaymentStatus.PENDING: {
        "background": "#fff4db",
        "border": "#ffd27a",
        "color": "#8a5a00",
    },
    PaymentStatus.APPROVED: {
        "background": "#e7f9ef",
        "border": "#8ae0ae",
        "color": "#146c43",
    },
    PaymentStatus.REJECTED: {
        "background": "#ffe6e6",
        "border": "#ff9f9f",
        "color": "#a61b1b",
    },
    MembershipStatus.ACTIVE: {
        "background": "#e7f9ef",
        "border": "#8ae0ae",
        "color": "#146c43",
    },
    MembershipStatus.EXPIRED: {
        "background": "#ececec",
        "border": "#cfcfcf",
        "color": "#4b4b4b",
    },
    MembershipStatus.INACTIVE: {
        "background": "#ffe6e6",
        "border": "#ff9f9f",
        "color": "#a61b1b",
    },
    MembershipStatus.PENDING: {
        "background": "#fff4db",
        "border": "#ffd27a",
        "color": "#8a5a00",
    },
}


def _status_badge(label, status_key):
    style = STATUS_BADGE_STYLES.get(
        status_key,
        {"background": "#ececec", "border": "#cfcfcf", "color": "#4b4b4b"},
    )
    return format_html(
        (
            '<span style="display:inline-flex;align-items:center;padding:0.32rem 0.7rem;'
            'border-radius:999px;border:1px solid {};background:{};color:{};'
            'font-weight:700;font-size:0.75rem;letter-spacing:0.04em;text-transform:uppercase;">'
            "{}</span>"
        ),
        style["border"],
        style["background"],
        style["color"],
        label,
    )


class MembershipStatusListFilter(admin.SimpleListFilter):
    title = "membership status"
    parameter_name = "membership_status"

    def lookups(self, request, model_admin):
        return MembershipStatus.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(membership__membership_status=self.value())
        return queryset


class MembershipPlanListFilter(admin.SimpleListFilter):
    title = "membership plan"
    parameter_name = "membership_plan"

    def lookups(self, request, model_admin):
        plan_names = (
            Membership.objects.order_by("plan_name")
            .values_list("plan_name", flat=True)
            .distinct()
        )
        return [(plan_name, plan_name) for plan_name in plan_names]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(membership__plan_name=self.value())
        return queryset


def _apply_payment_decision(proof, *, approve):
    if approve:
        proof.approve(admin_note=proof.admin_note or None)
        return "approved"
    proof.reject(admin_note=proof.admin_note or None)
    return "rejected"


@admin.action(description="Approve selected payments")
def approve_selected_payments(modeladmin, request, queryset):
    approved_count = 0
    for proof in queryset.select_related("membership", "user"):
        if proof.payment_status != PaymentStatus.APPROVED:
            _apply_payment_decision(proof, approve=True)
            approved_count += 1

    modeladmin.message_user(
        request,
        f"{approved_count} payment submission(s) approved successfully.",
        level=messages.SUCCESS,
    )


@admin.action(description="Reject selected payments")
def reject_selected_payments(modeladmin, request, queryset):
    rejected_count = 0
    for proof in queryset.select_related("membership", "user"):
        if proof.payment_status != PaymentStatus.REJECTED:
            _apply_payment_decision(proof, approve=False)
            rejected_count += 1

    modeladmin.message_user(
        request,
        f"{rejected_count} payment submission(s) rejected successfully.",
        level=messages.WARNING,
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at")
    search_fields = ("name", "email", "subject", "message")
    list_filter = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Gym_user)
class GymUserAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "username", "user", "date_of_joining")
    search_fields = ("first_name", "last_name", "username", "email", "user__username")
    list_filter = ("date_of_joining", "gender", "gym_split", "muscle_strength")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "member_account",
        "plan_name",
        "amount",
        "duration",
        "payment_status_badge",
        "membership_status_badge",
        "start_date",
        "expiry_date",
        "created_at",
    )
    list_filter = ("payment_status", "membership_status", "plan_name", "created_at")
    search_fields = ("user__username", "user__email", "plan_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "payment_status_badge", "membership_status_badge")
    fieldsets = (
        (
            "Membership Details",
            {
                "fields": (
                    "user",
                    "plan_name",
                    "amount",
                    "duration",
                    "start_date",
                    "expiry_date",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "payment_status",
                    "payment_status_badge",
                    "membership_status",
                    "membership_status_badge",
                    "created_at",
                )
            },
        ),
    )

    def get_queryset(self, request):
        Membership.expire_overdue_memberships()
        return super().get_queryset(request).select_related("user")

    @admin.display(description="User", ordering="user__username")
    def member_account(self, obj):
        return obj.user.username

    @admin.display(description="Payment Status", ordering="payment_status")
    def payment_status_badge(self, obj):
        return _status_badge(obj.get_payment_status_display(), obj.payment_status)

    @admin.display(description="Membership Status", ordering="membership_status")
    def membership_status_badge(self, obj):
        return _status_badge(obj.get_membership_status_display(), obj.membership_status)


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    change_form_template = "admin/Gym/paymentproof/change_form.html"
    list_display = (
        "member_account",
        "member_email",
        "membership_plan",
        "membership_amount",
        "utr_number",
        "payment_status_badge",
        "membership_status_badge",
        "uploaded_at",
        "screenshot_thumbnail",
    )
    list_filter = (
        "payment_status",
        MembershipStatusListFilter,
        MembershipPlanListFilter,
        "uploaded_at",
        "payment_method",
    )
    search_fields = ("user__username", "user__email", "utr_number", "membership__plan_name")
    actions = (approve_selected_payments, reject_selected_payments)
    ordering = ("-uploaded_at",)
    date_hierarchy = "uploaded_at"
    list_select_related = ("user", "membership")
    readonly_fields = (
        "member_account",
        "member_email",
        "membership",
        "membership_plan",
        "membership_amount",
        "membership_duration",
        "payment_method",
        "utr_number",
        "uploaded_at",
        "screenshot",
        "screenshot_preview",
        "payment_status_badge",
        "membership_status_badge",
    )
    fieldsets = (
        (
            "Member Details",
            {
                "fields": (
                    "member_account",
                    "member_email",
                    "membership",
                    "membership_plan",
                    "membership_amount",
                    "membership_duration",
                )
            },
        ),
        (
            "Verification",
            {
                "fields": (
                    "payment_status",
                    "payment_status_badge",
                    "membership_status_badge",
                    "admin_note",
                )
            },
        ),
        (
            "Payment Proof",
            {
                "fields": (
                    "payment_method",
                    "utr_number",
                    "uploaded_at",
                    "screenshot",
                    "screenshot_preview",
                )
            },
        ),
    )

    def get_queryset(self, request):
        Membership.expire_overdue_memberships()
        return super().get_queryset(request).select_related("user", "membership")

    def has_add_permission(self, request):
        return False

    def response_change(self, request, obj):
        if "_approve-payment" in request.POST:
            _apply_payment_decision(obj, approve=True)
            self.message_user(
                request,
                "Payment approved successfully. Membership activated automatically.",
                level=messages.SUCCESS,
            )
            return HttpResponseRedirect(request.path)

        if "_reject-payment" in request.POST:
            _apply_payment_decision(obj, approve=False)
            self.message_user(
                request,
                "Payment rejected successfully. Membership marked inactive.",
                level=messages.WARNING,
            )
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    @admin.display(description="User", ordering="user__username")
    def member_account(self, obj):
        return obj.user.username

    @admin.display(description="Email", ordering="user__email")
    def member_email(self, obj):
        return obj.user.email or "-"

    @admin.display(description="Plan", ordering="membership__plan_name")
    def membership_plan(self, obj):
        return obj.membership.plan_name

    @admin.display(description="Amount", ordering="membership__amount")
    def membership_amount(self, obj):
        return f"Rs {obj.membership.amount:,.2f}"

    @admin.display(description="Duration", ordering="membership__duration")
    def membership_duration(self, obj):
        return f"{obj.membership.duration} days"

    @admin.display(description="Payment Status", ordering="payment_status")
    def payment_status_badge(self, obj):
        return _status_badge(obj.get_payment_status_display(), obj.payment_status)

    @admin.display(description="Membership Status", ordering="membership__membership_status")
    def membership_status_badge(self, obj):
        membership = obj.membership
        membership.expire_if_needed(save=True)
        return _status_badge(
            membership.get_membership_status_display(),
            membership.membership_status,
        )

    @admin.display(description="Screenshot")
    def screenshot_thumbnail(self, obj):
        if not obj.screenshot:
            return "No screenshot"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">'
            '<img src="{}" alt="Payment proof" '
            'style="height:58px;width:58px;object-fit:cover;border-radius:10px;border:1px solid #d7d7d7;" /></a>',
            obj.screenshot.url,
            obj.screenshot.url,
        )

    @admin.display(description="Screenshot Preview")
    def screenshot_preview(self, obj):
        if not obj.screenshot:
            return "No screenshot uploaded"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">'
            '<img src="{}" alt="Payment proof" '
            'style="max-height:180px;max-width:240px;border-radius:12px;border:1px solid #d7d7d7;box-shadow:0 6px 18px rgba(0,0,0,0.12);" />'
            "</a>",
            obj.screenshot.url,
            obj.screenshot.url,
        )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("member", "date", "status", "updated_at")
    list_filter = ("status", "date")
    search_fields = ("member__first_name", "member__last_name", "member__username")
    ordering = ("-date",)


admin.site.register(Gym_split)
admin.site.register(Address)
admin.site.register(Gender)
admin.site.register(Muscle_strength)
