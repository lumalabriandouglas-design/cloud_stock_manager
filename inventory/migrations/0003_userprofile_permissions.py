from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_userprofile_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="can_manage_stock",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_edit_items",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_view_reports",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_manage_categories",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_manage_team",
            field=models.BooleanField(default=False),
        ),
    ]
