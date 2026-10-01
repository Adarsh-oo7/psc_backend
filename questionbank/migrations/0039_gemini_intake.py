from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questionbank", "0038_userprofile_practice_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="currentaffairs",
            name="is_published",
            field=models.BooleanField(
                default=True,
                help_text="Unpublished items stay in the admin until someone checks the fact.",
            ),
        ),
        migrations.CreateModel(
            name="GeminiIntakeSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=False, help_text="When this is off, the daily job does nothing.")),
                ("hold_for_review", models.BooleanField(default=True, help_text="Save new questions as pending. Students see them only after Approve.")),
                ("daily_accept_cap", models.PositiveIntegerField(default=40, help_text="Most questions saved in one day, across every Google project.")),
                ("requests_per_project_per_day", models.PositiveIntegerField(default=30, help_text="Our cap per Google project. The free tier allows more, but this keeps the run small.")),
                ("questions_per_request", models.PositiveIntegerField(default=5, help_text="How many questions to ask for in one Gemini call.")),
                ("max_calls_per_run", models.PositiveIntegerField(default=12, help_text="Stop after this many Gemini calls, even if the daily cap is not full.")),
                ("run_current_affairs", models.BooleanField(default=True, help_text="Also ask for today's current affairs. Those stay unpublished until an admin ticks them.")),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("last_report", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Gemini intake",
                "verbose_name_plural": "Gemini intake",
            },
        ),
        migrations.CreateModel(
            name="GeminiProjectUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("project_number", models.CharField(max_length=32)),
                ("day", models.DateField()),
                ("requests", models.PositiveIntegerField(default=0)),
                ("accepted", models.PositiveIntegerField(default=0)),
                ("rejected", models.PositiveIntegerField(default=0)),
                ("duplicates", models.PositiveIntegerField(default=0)),
                ("last_error", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "Gemini project usage",
                "verbose_name_plural": "Gemini project usage",
                "ordering": ["-day", "project_number"],
                "unique_together": {("project_number", "day")},
            },
        ),
    ]
