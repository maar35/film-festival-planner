# Generated by Django 3.2.9 on 2022-06-05 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filmList', '0016_reload_fan_ratings'),
    ]

    operations = [
        migrations.CreateModel(
            name='TableColor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('border_color', models.CharField(choices=[('red', 'red'), ('maroon', 'maroon'), ('green', 'green'), ('lime', 'lime'), ('blue', 'blue'), ('navy', 'navy'), ('black', 'black')], default='lime', max_length=10)),
            ],
            options={
                'db_table': 'table_color',
            },
        ),
    ]
