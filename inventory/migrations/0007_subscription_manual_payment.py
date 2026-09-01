from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0006_subscription"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="payment_phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="subscription",
            name="payment_tx_id",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="subscription",
            name="payment_note",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="subscription",
            name="payment_claimed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="status",
            field=models.CharField(
                choices=[
                    ("trial", "Trial"),
                    ("active", "Active"),
                    ("pending", "Pending verification"),
                    ("past_due", "Past due"),
                    ("suspended", "Suspended"),
                ],
                default="trial",
                max_length=20,
            ),
        ),
        migrations.RemoveField(
            model_name="subscription",
            name="flutterwave_tx_ref",
        ),
    ]
