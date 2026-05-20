from django.db import models


class Exercise(models.Model):
    GROUP_IMAGE_MAP = {
        "chest": "exercises/chest.png",
        "back": "exercises/back.png",
        "shoulders": "exercises/shoulder.png",
        "biceps": "exercises/bicep_tricep.png",
        "triceps": "exercises/bicep_tricep.png",
        "forearms": "exercises/bicep_tricep.png",
        "legs": "exercises/leg.png",
    }

    class MuscleGroup(models.TextChoices):
        CHEST = "chest", "Chest"
        BACK = "back", "Back"
        SHOULDERS = "shoulders", "Shoulders"
        BICEPS = "biceps", "Biceps"
        TRICEPS = "triceps", "Triceps"
        FOREARMS = "forearms", "Forearms"
        LEGS = "legs", "Legs"

    name = models.CharField(max_length=150, unique=True)
    muscle_group = models.CharField(max_length=20, choices=MuscleGroup.choices, db_index=True)
    instructions = models.TextField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    image = models.ImageField(upload_to="exercises/", blank=True, null=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    @property
    def fallback_static_image(self):
        return self.GROUP_IMAGE_MAP.get(self.muscle_group, "exercises/push.png")

    @classmethod
    def library_context(cls, selected_group=""):
        valid_groups = {value: label for value, label in cls.MuscleGroup.choices}
        selected_group = (selected_group or "").strip().lower()
        if selected_group not in valid_groups:
            selected_group = ""

        exercises = list(cls.objects.all())
        group_counts = {
            value: sum(1 for exercise in exercises if exercise.muscle_group == value)
            for value, _ in cls.MuscleGroup.choices
        }

        exercise_groups = []
        for value, label in cls.MuscleGroup.choices:
            if selected_group and value != selected_group:
                continue

            group_exercises = [
                exercise for exercise in exercises if exercise.muscle_group == value
            ]
            if not group_exercises:
                continue

            exercise_groups.append(
                {
                    "value": value,
                    "label": label,
                    "count": len(group_exercises),
                    "exercises": group_exercises,
                }
            )

        muscle_group_filters = [
            {
                "value": value,
                "label": label,
                "count": group_counts[value],
            }
            for value, label in cls.MuscleGroup.choices
            if group_counts[value]
        ]

        return {
            "exercise_groups": exercise_groups,
            "muscle_group_filters": muscle_group_filters,
            "selected_group": selected_group,
            "selected_group_label": valid_groups.get(selected_group, "All Muscle Groups"),
        }
