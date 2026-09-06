from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0009_invite_and_reset"),
    ]

    operations = [
        migrations.AddField(
            model_name="item",
            name="unit",
            field=models.CharField(
                choices=[("pcs", "Pieces"), ("kg", "Kilograms")],
                default="pcs",
                max_length=8,
            ),
        ),
        migrations.AlterField(
            model_name="item",
            name="quantity_in_stock",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name="item",
            name="reorder_level",
            field=models.DecimalField(decimal_places=3, default=5, max_digits=12),
        ),
        migrations.AlterField(
            model_name="sale",
            name="quantity_sold",
            field=models.DecimalField(decimal_places=3, default=1, max_digits=12),
        ),
        migrations.AlterField(
            model_name="stockin",
            name="quantity_added",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
    ]
