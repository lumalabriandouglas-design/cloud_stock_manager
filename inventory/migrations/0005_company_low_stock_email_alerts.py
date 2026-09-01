from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_activitylog"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="low_stock_email_alerts",
            field=models.BooleanField(default=True),
        ),
    ]
