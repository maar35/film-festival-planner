# Generated by Django 3.2.9 on 2022-07-28 21:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('festivals', '0012_remove_festival_is_current_festival'),
    ]

    operations = [
        migrations.AddField(
            model_name='festival',
            name='festival_color',
            field=models.CharField(choices=[('tomato', 'tomato'), ('red', 'red'), ('orange', 'orange'), ('maroon', 'maroon'), ('yellow', 'yellow'), ('lime', 'lime'), ('green', 'green'), ('olive', 'olive'), ('turquoise', 'turquoise'), ('blue', 'blue'), ('navy', 'navy'), ('fuchsia', 'fuchsia'), ('purple', 'purple'), ('silver', 'silver'), ('grey', 'grey'), ('black', 'black')], default='green', max_length=24),
        ),
    ]
