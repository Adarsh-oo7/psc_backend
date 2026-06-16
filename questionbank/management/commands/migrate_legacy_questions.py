from django.core.management.base import BaseCommand
from questionbank.models import Questions, Question, Topic

class Command(BaseCommand):
    help = "Migrates questions from the legacy Questions model (uppercase S) to the main Question model"

    def handle(self, *args, **kwargs):
        default_topic, _ = Topic.objects.get_or_create(
            name="General",
            defaults={'slug': 'general'}
        )
        
        legacy_qs = Questions.objects.all()
        total_count = legacy_qs.count()
        self.stdout.write(f"Found {total_count} legacy questions to migrate.")

        migrated_count = 0
        for old_q in legacy_qs:
            q, created = Question.objects.get_or_create(
                text=old_q.question_text,
                defaults={
                    'options': {
                        'A': old_q.option_a,
                        'B': old_q.option_b,
                        'C': old_q.option_c,
                        'D': old_q.option_d,
                    },
                    'correct_answer': old_q.correct_answer,
                    'explanation': old_q.explanation,
                    'topic': default_topic,
                    'difficulty': 'medium',
                }
            )
            if created:
                migrated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Migration complete! Migrated {migrated_count} new questions to main Question model."))
