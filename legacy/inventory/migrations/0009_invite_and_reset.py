from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0008_userprofile_last_seen"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffInvite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("role", models.CharField(choices=[("owner", "Owner"), ("staff", "Staff")], default="staff", max_length=20)),
                ("can_manage_stock", models.BooleanField(default=True)),
                ("can_edit_items", models.BooleanField(default=True)),
                ("can_view_reports", models.BooleanField(default=True)),
                ("can_manage_categories", models.BooleanField(default=False)),
                ("can_manage_team", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invites", to="inventory.company")),
            ],
            options={"unique_together": {("company", "email")}},
        ),
        migrations.CreateModel(
            name="PasswordResetCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code_hash", models.CharField(max_length=64)),
                ("expires_at", models.DateTimeField()),
                ("used", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reset_codes", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
