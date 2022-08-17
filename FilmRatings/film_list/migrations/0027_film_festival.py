# Generated by Django 3.2.9 on 2022-08-06 16:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('festivals', '0014_remove_festival_border_color'),
        ('film_list', '0026_filmfan_is_admin'),
    ]

    operations = [
        migrations.AddField(
            model_name='film',
            name='festival',
            field=models.ForeignKey(default=2, on_delete=django.db.models.deletion.CASCADE, to='festivals.festival'),
            preserve_default=False,
        ),
    ]
