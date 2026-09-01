# Generated manually for role field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[("owner", "Owner"), ("staff", "Staff")],
                default="owner",
                max_length=20,
            ),
        ),
    ]
