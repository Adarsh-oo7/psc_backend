# Generated by Django 5.1.6 on 2025-06-30 14:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("questionbank", "0011_copy_exam_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="question",
            name="old_exam",
        ),
    ]
