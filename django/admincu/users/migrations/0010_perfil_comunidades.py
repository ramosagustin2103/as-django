# Generated by Django 2.2.7 on 2021-04-27 19:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0003_auto_20210317_1916'),
        ('users', '0009_auto_20191104_1924'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfil',
            name='comunidades',
            field=models.ManyToManyField(blank=True, related_name='admins', to='utils.Comunidad'),
        ),
    ]