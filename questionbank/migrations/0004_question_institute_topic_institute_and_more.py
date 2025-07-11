# Generated by Django 5.1.6 on 2025-06-11 19:25

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("institutes", "0001_initial"),
        ("questionbank", "0003_question_difficulty_alter_topic_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="institute",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="questions",
                to="institutes.institute",
            ),
        ),
        migrations.AddField(
            model_name="topic",
            name="institute",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="topics",
                to="institutes.institute",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="institute",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="members",
                to="institutes.institute",
            ),
        ),
    ]
