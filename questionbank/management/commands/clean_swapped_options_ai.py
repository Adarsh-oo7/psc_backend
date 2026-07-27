from django.core.management.base import BaseCommand
from django.db import transaction, connection
from questionbank.models import (
    Question, Report, UserAnswer, Bookmark, DailyExam, 
    ModelExam, PreviousYearPaper, SessionAnswer, AIExplanationCache
)
import os
import re
import hashlib
import json
import requests
import time

class Command(BaseCommand):
    help = "Scan KPSC questions using AI and replace mismatched/unrelated distractors with high-quality, relevant options"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50, help='Maximum number of bad questions to fix in this run')
        parser.add_argument('--batch-size', type=int, default=40, help='Number of questions to verify in each batch API call')
        parser.add_argument('--max-scan', type=int, help='Maximum number of questions to scan (safeguard)')
        parser.add_argument('--topic-id', type=int, help='Filter by Topic ID')
        parser.add_argument('--exam-id', type=int, help='Filter by Exam ID')
        parser.add_argument('--all', action='store_true', help='Process all questions without limit')

    def handle(self, *args, **options):
        api_key = os.environ.get('GEMINI_REPORT_API_KEY') or os.environ.get('GEMINI_API_KEY')
        if not api_key:
            self.stderr.write("API Key not found. Please set GEMINI_REPORT_API_KEY or GEMINI_API_KEY in .env.")
            return

        limit = options['limit']
        batch_size = options['batch_size']
        max_scan = options['max_scan']
        topic_id = options['topic_id']
        exam_id = options['exam_id']
        process_all = options['all']

        # Get questions
        queryset = Question.objects.all().order_by('id')
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        if exam_id:
            queryset = queryset.filter(exams__id=exam_id).distinct()

        self.stdout.write(f"Total candidate questions in filter: {queryset.count()}")

        # We will iterate through questions in batches to detect bad ones
        bad_question_ids = []
        questions_list = list(queryset)
        total_questions = len(questions_list)
        scanned_count = 0

        self.stdout.write("Step 1: Batch-scanning questions using AI and fixing mismatched options progressively...")

        fixed_count = 0
        merged_count = 0
        scanned_count = 0

        for i in range(0, total_questions, batch_size):
            if not process_all and fixed_count >= limit:
                self.stdout.write(f"Reached --limit of {limit} fixed questions. Stopping.")
                break
            
            if max_scan and scanned_count >= max_scan:
                self.stdout.write(f"Reached --max-scan limit of {max_scan} questions. Stopping.")
                break

            batch = questions_list[i:i + batch_size]
            scanned_count += len(batch)
            batch_data = []
            for q in batch:
                batch_data.append({
                    "id": q.id,
                    "question": q.text,
                    "options": q.options,
                    "correct_answer": q.correct_answer
                })

            self.stdout.write(f"Scanning batch {i // batch_size + 1} (IDs: {batch[0].id} to {batch[-1].id})...")
            
            detected_ids = self.detect_bad_options_batch(batch_data, api_key)
            if detected_ids:
                self.stdout.write(self.style.WARNING(f"  -> Detected bad options in IDs: {detected_ids}"))
                for bad_id in detected_ids:
                    if not process_all and fixed_count >= limit:
                        break
                    
                    try:
                        q = Question.objects.get(pk=bad_id)
                    except Question.DoesNotExist:
                        continue

                    self.stdout.write(f"    Fixing Question #{q.id}: \"{q.text[:60]}...\"")
                    fixed_data = self.generate_relevant_distractors(q, api_key)
                    if not fixed_data:
                        self.stdout.write(self.style.ERROR(f"    Failed to generate clean options for #{q.id}"))
                        continue

                    # Check duplicate hash before saving
                    normalized = re.sub(r'[^\w\s]', '', q.text).lower().strip()
                    normalized = re.sub(r'\s+', ' ', normalized)
                    if fixed_data['options'] and isinstance(fixed_data['options'], dict):
                        opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(fixed_data['options'].items()))
                        normalized = f"{normalized}||{opts_str}"
                    new_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                    existing_q = Question.objects.filter(text_hash=new_hash).exclude(pk=q.pk).first()

                    if existing_q:
                        self.merge_duplicate_questions(existing_q, q)
                        self.stdout.write(self.style.SUCCESS(f"    -> Matched existing Question #{existing_q.id}. Safely merged!"))
                        merged_count += 1
                    else:
                        q.options = fixed_data['options']
                        q.correct_answer = fixed_data['correct_answer']
                        q.explanation = fixed_data['explanation']
                        q.text_hash = new_hash
                        q.save()
                        self.stdout.write(self.style.SUCCESS(f"    -> Successfully fixed options for #{q.id}!"))
                        fixed_count += 1

                    time.sleep(1.5)
            
            # Simple rate limit throttling between batches
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS(
            f"\nClean run complete! Fixed questions: {fixed_count}, Merged duplicates: {merged_count}"
        ))

    def detect_bad_options_batch(self, batch_data, api_key):
        """Analyze batch of MCQs using Gemini to detect option mismatch (with retries)."""
        prompt = f"""You are an expert editor of Kerala PSC exam questions.
Analyze the following list of MCQs. For each question, determine if the 3 incorrect options (distractors) are completely unrelated, swapped, or of a different type compared to the question and the correct answer (e.g. if the question asks for a Person, but the incorrect options are years or concepts, or if they are obviously from different questions).

List of questions:
{json.dumps(batch_data, indent=2)}

Return ONLY a JSON list of question IDs that have unrelated or bad distractor options. Only return the bad IDs. Example: [35518]"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {'contents': [{'parts': [{'text': prompt}]}]}
        
        for attempt in range(3):
            try:
                res = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=60)
                if res.status_code == 200:
                    text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                    if text.startswith('```'):
                        text = text.split('```')[1]
                        if text.startswith('json'):
                            text = text[4:]
                    return json.loads(text.strip())
            except Exception as e:
                self.stdout.write(f"Error during detection batch (attempt {attempt + 1}/3): {e}")
                time.sleep(2 * (attempt + 1))
        return []

    def generate_relevant_distractors(self, q, api_key):
        """Call AI to generate 3 relevant distractors for a bad question (with retries)."""
        correct_val = q.options.get(q.correct_answer, '')
        
        prompt = f"""You are a Kerala PSC exam quality expert.
For the following MCQ question, the distractors (incorrect options) are completely unrelated or mismatched.
Please generate 3 new, high-quality, and highly relevant distractor options of the EXACT same category/type as the correct answer (e.g. if the correct answer is a person, all distractors must be plausible people of the same category/topic).

Question: "{q.text}"
Correct Option: Option {q.correct_answer} -> "{correct_val}"

RETURN ONLY THIS JSON (no markdown, no extra text):
{{
  "options": {{
    "A": "first option",
    "B": "second option",
    "C": "third option",
    "D": "fourth option"
  }},
  "correct_answer": "{q.correct_answer}",
  "explanation": "clear explanation why the correct answer is right and who the distractors are"
}}
"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {'contents': [{'parts': [{'text': prompt}]}]}
        
        for attempt in range(3):
            try:
                res = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=60)
                if res.status_code == 200:
                    text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                    if text.startswith('```'):
                        text = text.split('```')[1]
                        if text.startswith('json'):
                            text = text[4:]
                    return json.loads(text.strip())
            except Exception as e:
                self.stdout.write(f"Error generating distractors for Question #{q.id} (attempt {attempt + 1}/3): {e}")
                time.sleep(2 * (attempt + 1))
        return None

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
