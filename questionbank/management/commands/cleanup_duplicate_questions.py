from django.core.management.base import BaseCommand
from django.db.models import Count
from questionbank.models import Question


class Command(BaseCommand):
    help = 'Finds and removes duplicate questions based on the exact question text.'
    def handle(self, *args, **options):
        duplicate_texts = (
            Question.objects.values('text')
            .annotate(text_count=Count('text'))
            .filter(text_count__gt=1)
        )
        if not duplicate_texts.exists():
            self.stdout.write(self.style.SUCCESS("No duplicate questions found. Your database is already clean!"))
            return

        self.stdout.write(f"Found {len(duplicate_texts)} texts with duplicate questions. Starting cleanup...")
        
        total_deleted = 0
        for item in duplicate_texts:
            text = item['text']
            
            questions = Question.objects.filter(text=text).order_by('id')
            
            first_question_to_keep = questions.first()
            
            questions_to_delete = questions.exclude(pk=first_question_to_keep.pk)
            
            deleted_count, _ = questions_to_delete.delete()
            total_deleted += deleted_count
            
            self.stdout.write(f"  - Text: '{text[:50]}...'. Kept 1, deleted {deleted_count}.")
            
        self.stdout.write(self.style.SUCCESS(f"\nCleanup complete! Total duplicate questions removed: {total_deleted}"))