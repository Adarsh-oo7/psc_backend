from django.core.management.base import BaseCommand
from django.db import transaction
from questionbank.models import Question, Report, UserAnswer, Bookmark, DailyExam, ModelExam, PreviousYearPaper, SessionAnswer, AIExplanationCache
import re
import hashlib
import json

class Command(BaseCommand):
    help = "Normalize options keys to A,B,C,D, uppercase correct_answers, re-compute text_hashes, and merge duplicates"

    def handle(self, *args, **options):
        questions = Question.objects.all()
        total = questions.count()
        self.stdout.write(f"Found {total} questions to process.")

        processed = 0
        updated = 0
        merged = 0

        # We construct a list of IDs first because we delete questions during iteration
        q_ids = list(questions.values_list('id', flat=True))

        for q_id in q_ids:
            processed += 1
            if processed % 1000 == 0:
                self.stdout.write(f"Processed {processed}/{total}...")

            # Get fresh from DB
            try:
                q = Question.objects.get(pk=q_id)
            except Question.DoesNotExist:
                continue

            changed = False
            
            # 1. Parse and normalize options
            opts = q.options
            if isinstance(opts, str):
                try:
                    opts = json.loads(opts)
                    changed = True
                except Exception:
                    opts = {}
            
            if isinstance(opts, dict):
                norm_opts = {}
                for k, v in opts.items():
                    key_upper = str(k).upper()
                    if key_upper != k:
                        changed = True
                    norm_opts[key_upper] = str(v)
                
                # Check for missing keys and add empty defaults
                for key in ['A', 'B', 'C', 'D']:
                    if key not in norm_opts:
                        norm_opts[key] = ""
                        changed = True
                
                if changed or q.options != norm_opts:
                    q.options = norm_opts
                    changed = True

            # 2. Normalize correct_answer
            correct = q.correct_answer
            if correct:
                correct_upper = str(correct).strip().upper()
                if correct_upper != q.correct_answer:
                    q.correct_answer = correct_upper
                    changed = True

            if changed or not q.text_hash:
                # Calculate new text hash beforehand to check for duplicates
                normalized = re.sub(r'[^\w\s]', '', q.text).lower().strip()
                normalized = re.sub(r'\s+', ' ', normalized)
                if q.options and isinstance(q.options, dict):
                    opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(q.options.items()))
                    normalized = f"{normalized}||{opts_str}"
                new_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                # Check if another question already has this hash
                existing_q = Question.objects.filter(text_hash=new_hash).exclude(pk=q.pk).first()

                if existing_q:
                    # Merge duplicate question
                    self.merge_duplicate_questions(existing_q, q)
                    merged += 1
                else:
                    q.text_hash = new_hash
                    q.save()
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Completed! Processed: {processed}, Updated: {updated}, Merged duplicates: {merged}"
        ))

    def merge_duplicate_questions(self, existing_q, duplicate_q):
        """Merges duplicate_q into existing_q, re-pointing all relationships, and deletes duplicate_q."""
        with transaction.atomic():
            # 1. UserAnswer
            UserAnswer.objects.filter(question=duplicate_q).update(question=existing_q)
            
            # 2. Bookmark
            for b in Bookmark.objects.filter(question=duplicate_q):
                if not Bookmark.objects.filter(user=b.user, question=existing_q).exists():
                    b.question = existing_q
                    b.save()
                else:
                    b.delete()

            # 3. Report
            Report.objects.filter(question=duplicate_q).update(question=existing_q)

            # 4. DailyExam (ManyToMany)
            for de in DailyExam.objects.filter(questions=duplicate_q):
                de.questions.remove(duplicate_q)
                de.questions.add(existing_q)

            # 5. ModelExam (ManyToMany)
            for me in ModelExam.objects.filter(questions=duplicate_q):
                me.questions.remove(duplicate_q)
                me.questions.add(existing_q)

            # 6. PreviousYearPaper (ManyToMany)
            for pyp in PreviousYearPaper.objects.filter(questions=duplicate_q):
                pyp.questions.remove(duplicate_q)
                pyp.questions.add(existing_q)

            # 7. SessionAnswer (Inline Session Answers)
            for sa in SessionAnswer.objects.filter(question=duplicate_q):
                if not SessionAnswer.objects.filter(session=sa.session, question=existing_q).exists():
                    sa.question = existing_q
                    sa.save()
                else:
                    sa.delete()

            # 8. AIExplanationCache
            for cache in AIExplanationCache.objects.filter(question=duplicate_q):
                if not AIExplanationCache.objects.filter(question=existing_q, language=cache.language).exists():
                    cache.question = existing_q
                    cache.save()
                else:
                    cache.delete()

            # 9. Update stats on existing_q
            existing_q.times_answered += duplicate_q.times_answered
            existing_q.times_correct += duplicate_q.times_correct
            existing_q.times_appeared += duplicate_q.times_appeared
            existing_q.save()

            # 10. Delete duplicate_q
            duplicate_q.delete()
