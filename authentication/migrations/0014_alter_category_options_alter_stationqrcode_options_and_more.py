# Generated by Django 5.0.4 on 2024-10-26 07:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0013_alter_journey_emission_saved'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='category',
            options={'verbose_name_plural': 'Categories'},
        ),
        migrations.AlterModelOptions(
            name='stationqrcode',
            options={'verbose_name_plural': 'Station QR Codes'},
        ),
        migrations.AlterModelOptions(
            name='tags',
            options={'verbose_name_plural': 'Tags'},
        ),
    ]
