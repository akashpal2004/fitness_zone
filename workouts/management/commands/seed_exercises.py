from django.core.management.base import BaseCommand

from workouts.models import Exercise


EXERCISE_DATA = {
    Exercise.MuscleGroup.CHEST: [
        {
            "name": "Bench Press",
            "instructions": "Lie flat on the bench, lower the bar to mid-chest with control, then press upward until your arms are extended.",
        },
        {
            "name": "Push-ups",
            "instructions": "Keep your body in a straight line, lower your chest toward the floor, then push back up through your palms.",
        },
        {
            "name": "Incline Dumbbell Press",
            "instructions": "Set the bench to an incline, lower the dumbbells beside your upper chest, then press them upward in a controlled path.",
        },
    ],
    Exercise.MuscleGroup.BACK: [
        {
            "name": "Pull-ups",
            "instructions": "Hang from the bar with a firm grip, pull your chest toward the bar, then lower slowly to a full stretch.",
        },
        {
            "name": "Deadlift",
            "instructions": "Brace your core, keep the bar close to your legs, drive through your heels, and stand tall before lowering with control.",
        },
        {
            "name": "Seated Cable Row",
            "instructions": "Sit tall, pull the handle toward your lower ribs, squeeze your shoulder blades, then return without rounding your back.",
        },
    ],
    Exercise.MuscleGroup.SHOULDERS: [
        {
            "name": "Shoulder Press",
            "instructions": "Start with the weights at shoulder level, press overhead until your arms extend, then lower back under control.",
        },
        {
            "name": "Lateral Raises",
            "instructions": "Raise the dumbbells out to your sides until shoulder height with a soft elbow bend, then lower slowly.",
        },
        {
            "name": "Front Raises",
            "instructions": "Lift the weights straight in front of you to shoulder height, pause briefly, then lower without swinging.",
        },
    ],
    Exercise.MuscleGroup.BICEPS: [
        {
            "name": "Bicep Curls",
            "instructions": "Keep your elbows close to your torso, curl the weights toward your shoulders, then lower them with control.",
        },
        {
            "name": "Hammer Curls",
            "instructions": "Hold the dumbbells with palms facing inward, curl to shoulder level, and lower slowly while keeping your elbows fixed.",
        },
        {
            "name": "Concentration Curls",
            "instructions": "Rest your elbow against your inner thigh, curl the weight toward your shoulder, then lower through the full range.",
        },
    ],
    Exercise.MuscleGroup.TRICEPS: [
        {
            "name": "Tricep Dips",
            "instructions": "Lower your body by bending your elbows, keep your chest up, then press back until your arms are nearly straight.",
        },
        {
            "name": "Tricep Pushdowns",
            "instructions": "Keep your elbows pinned at your sides, press the handle down until your arms extend, then return slowly.",
        },
        {
            "name": "Overhead Tricep Extension",
            "instructions": "Hold the weight overhead, bend your elbows to lower it behind your head, then extend upward again.",
        },
    ],
    Exercise.MuscleGroup.FOREARMS: [
        {
            "name": "Wrist Curls",
            "instructions": "Rest your forearms on a bench or thighs with palms up, curl the weight with your wrists, and lower slowly.",
        },
        {
            "name": "Reverse Wrist Curls",
            "instructions": "With palms facing down, lift the weight using only your wrists, then return under control.",
        },
        {
            "name": "Farmer's Walk",
            "instructions": "Stand tall with heavy weights at your sides, brace your core, and walk steadily without leaning.",
        },
    ],
    Exercise.MuscleGroup.LEGS: [
        {
            "name": "Squats",
            "instructions": "Sit your hips back and down, keep your chest up and knees tracking over your feet, then stand back up strongly.",
        },
        {
            "name": "Lunges",
            "instructions": "Step forward, lower until both knees bend comfortably, then drive through your front heel to return.",
        },
        {
            "name": "Leg Press",
            "instructions": "Place your feet shoulder-width on the platform, lower with control, then press through your heels to extend.",
        },
    ],
}


class Command(BaseCommand):
    help = "Seed default exercises without creating duplicates."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for muscle_group, exercises in EXERCISE_DATA.items():
            for exercise in exercises:
                _, created = Exercise.objects.update_or_create(
                    name=exercise["name"],
                    defaults={
                        "muscle_group": muscle_group,
                        "instructions": exercise["instructions"],
                        "image_url": exercise.get("image_url", ""),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Exercises seeded successfully. Created: {created_count}, updated: {updated_count}."
            )
        )
