from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0012_debts"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="reminded_upcoming_for",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="reminded_due_for",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
