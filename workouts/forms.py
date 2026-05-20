from django import forms

from .models import Exercise


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ["name", "muscle_group", "instructions", "image", "image_url"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter exercise name",
                    "maxlength": 150,
                }
            ),
            "muscle_group": forms.Select(
                attrs={
                    "class": "form-control custom-select",
                }
            ),
            "instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Describe how to perform this exercise",
                    "rows": 5,
                }
            ),
            "image": forms.FileInput(
                attrs={
                    "class": "form-control form-control-file",
                    "accept": "image/*",
                }
            ),
            "image_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com/exercise-image.jpg",
                }
            ),
        }

    def clean_name(self):
        return " ".join((self.cleaned_data.get("name") or "").split())

    def clean_instructions(self):
        return " ".join((self.cleaned_data.get("instructions") or "").split())
