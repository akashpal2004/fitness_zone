from django.shortcuts import render

from .models import Exercise


def home(request):
    featured_exercises = Exercise.objects.all()[:3]
    return render(request, "home.html", {"featured_exercises": featured_exercises})


def exercises(request):
    exercise_context = Exercise.library_context(request.GET.get("group"))
    return render(
        request,
        "workouts/exercises.html",
        exercise_context,
    )
