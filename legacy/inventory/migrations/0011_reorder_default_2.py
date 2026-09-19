from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0010_item_units"),
    ]

    operations = [
        migrations.AlterField(
            model_name="item",
            name="reorder_level",
            field=models.DecimalField(decimal_places=3, default=2, max_digits=12),
        ),
    ]
