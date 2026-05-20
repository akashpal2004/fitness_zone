from django.db import migrations


def backfill_auth_users(apps, schema_editor):
    GymUser = apps.get_model("Gym", "Gym_user")
    AuthUser = apps.get_model("auth", "User")

    for profile in GymUser.objects.all():
        username = (profile.username or "").strip()
        if not username:
            continue

        auth_user = AuthUser.objects.filter(username__iexact=username).first()
        if auth_user is None:
            auth_user = AuthUser.objects.create_user(
                username=username,
                email=profile.email or "",
                password=profile.password or None,
            )
            auth_user.first_name = profile.first_name or ""
            auth_user.last_name = profile.last_name or ""
            auth_user.save(update_fields=["first_name", "last_name"])
        else:
            updated_fields = []
            if not auth_user.email and profile.email:
                auth_user.email = profile.email
                updated_fields.append("email")
            if not auth_user.first_name and profile.first_name:
                auth_user.first_name = profile.first_name
                updated_fields.append("first_name")
            if not auth_user.last_name and profile.last_name:
                auth_user.last_name = profile.last_name
                updated_fields.append("last_name")
            if profile.password and not auth_user.has_usable_password():
                auth_user.set_password(profile.password)
                updated_fields.append("password")
            if updated_fields:
                auth_user.save(update_fields=updated_fields)

        profile.user_id = auth_user.id
        profile.email = auth_user.email or profile.email
        profile.password = ""
        profile.save(update_fields=["user", "email", "password"])


class Migration(migrations.Migration):

    dependencies = [
        ("Gym", "0006_gym_user_user_alter_gym_user_email_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_auth_users, migrations.RunPython.noop),
    ]
