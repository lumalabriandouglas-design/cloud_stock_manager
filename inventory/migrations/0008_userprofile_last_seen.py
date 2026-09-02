from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0007_subscription_manual_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="last_seen",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
