from django.contrib import admin
from django.templatetags.static import static
from django.utils.html import format_html

from .models import Exercise


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "name", "muscle_group")
    list_filter = ("muscle_group",)
    search_fields = ("name", "instructions")
    readonly_fields = ("image_preview",)
    fieldsets = (
        (
            "Exercise Details",
            {
                "fields": (
                    "name",
                    "muscle_group",
                    "instructions",
                    "image",
                    "image_url",
                    "image_preview",
                )
            },
        ),
    )

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if not obj:
            return "Add an uploaded image or save to use the default image."
        if obj.image:
            image_source = obj.image.url
        elif obj.image_url:
            image_source = obj.image_url
        else:
            image_source = static("exercises/default.png")
        return format_html(
            '<img src="{}" alt="{}" style="width:72px;height:72px;object-fit:cover;border-radius:14px;border:1px solid #d7d7d7;" />',
            image_source,
            obj.name,
        )
