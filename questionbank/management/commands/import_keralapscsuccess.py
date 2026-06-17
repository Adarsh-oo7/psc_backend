import re
import hashlib
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from questionbank.models import Question, Topic, Exam, ExamCategory

class Command(BaseCommand):
    help = "Ingests questions from keralapscsuccess.blogspot.com"

    def add_arguments(self, parser):
        parser.add_argument('--max-posts', type=int, default=50, help="Max number of posts to fetch")
        parser.add_argument('--domain', type=str, default='keralapscsuccess.blogspot.com', help="Blogger blogspot domain name")
        parser.add_argument('--dry-run', action='store_true', help="Dry run without saving to database")

    def handle(self, *args, **options):
        max_posts = options['max_posts']
        domain = options['domain']
        dry_run = options['dry_run']

        self.stdout.write(f"Starting ingestion from {domain}...")

        feed_url = f"https://{domain}/feeds/posts/default?alt=json&max-results={max_posts}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            res = requests.get(feed_url, headers=headers, timeout=15)
            if res.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Failed to fetch feed: HTTP {res.status_code}"))
                return

            data = res.json()
            entries = data.get('feed', {}).get('entry', [])
            if not entries:
                self.stdout.write("No posts found in feed.")
                return

            self.stdout.write(f"Processing {len(entries)} posts...")

            general_psc_exam, _ = Exam.objects.get_or_create(
                name="General PSC (2025)",
                defaults={
                    'year': 2025,
                    'category': ExamCategory.objects.first() or ExamCategory.objects.create(name="PSC", order=1)
                }
            )

            topic_name = "General Knowledge"
            topic_slug = slugify(topic_name) or 'general-knowledge'
            topic_obj = None
            if not dry_run:
                topic_obj, _ = Topic.objects.get_or_create(
                    slug=topic_slug,
                    defaults={'name': topic_name}
                )

            questions_imported = 0
            duplicates_skipped = 0
            errors_count = 0

            for entry in entries:
                post_title = entry.get('title', {}).get('$t', 'Mock Test Post')
                html_content = entry.get('content', {}).get('$t', '')

                # Prevent console encoding issues on Windows
                safe_title = post_title.encode('ascii', errors='replace').decode('ascii')
                self.stdout.write(f"\nParsing post: {safe_title}")
                soup = BeautifulSoup(html_content, 'html.parser')
                text_lines = [line.strip() for line in soup.get_text(separator='\n').split('\n') if line.strip()]

                parsed_questions = []
                i = 0
                while i < len(text_lines):
                    line = text_lines[i]
                    # Look for lines starting with a number e.g. "1." or "1:"
                    if re.match(r'^\d+[\s\.\:]+', line):
                        # Attempt to parse MCQ with next 5 lines
                        if i + 5 < len(text_lines):
                            opt_a = text_lines[i+1]
                            opt_b = text_lines[i+2]
                            opt_c = text_lines[i+3]
                            opt_d = text_lines[i+4]
                            ans_line = text_lines[i+5]

                            # Match options format like A) or A.
                            match_a = re.match(r'^[aA][\)\.]\s*(.*)', opt_a)
                            match_b = re.match(r'^[bB][\)\.]\s*(.*)', opt_b)
                            match_c = re.match(r'^[cC][\)\.]\s*(.*)', opt_c)
                            match_d = re.match(r'^[dD][\)\.]\s*(.*)', opt_d)
                            match_ans = re.match(r'^(?:answer|ans)\s*[:\-–]?\s*(.*)', ans_line, re.I)

                            if match_a and match_b and match_c and match_d and match_ans:
                                q_text = re.sub(r'^\d+[\s\.\:]+', '', line).strip()
                                q_text = re.sub(r'\s+', ' ', q_text).strip()

                                val_a = match_a.group(1).strip()
                                val_b = match_b.group(1).strip()
                                val_c = match_c.group(1).strip()
                                val_d = match_d.group(1).strip()
                                ans_val = match_ans.group(1).strip()

                                # Clean Option suffix from answer if present (e.g. "Option B" -> "B")
                                ans_clean = re.sub(r'^option\s*', '', ans_val, flags=re.I).strip().upper()

                                # Map correct answer letter
                                correct_letter = 'A'
                                if ans_clean in ('A', 'B', 'C', 'D'):
                                    correct_letter = ans_clean
                                else:
                                    # Fallback substring matching
                                    options_dict = {'A': val_a, 'B': val_b, 'C': val_c, 'D': val_d}
                                    for letter, opt_val in options_dict.items():
                                        if opt_val.lower().strip() in ans_val.lower().strip():
                                            correct_letter = letter
                                            break

                                parsed_questions.append({
                                    'text': q_text,
                                    'options': {'A': val_a, 'B': val_b, 'C': val_c, 'D': val_d},
                                    'correct_answer': correct_letter,
                                })
                                i += 6
                                continue
                    i += 1

                if not parsed_questions:
                    self.stdout.write(self.style.WARNING("  No parseable MCQ questions found. Skipping."))
                    continue

                self.stdout.write(f"  Found {len(parsed_questions)} questions. Saving...")
                
                try:
                    with transaction.atomic():
                        for q_data in parsed_questions:
                            question_text = q_data['text']
                            options_dict = q_data['options']
                            correct_answer = q_data['correct_answer']

                            normalized = re.sub(r'[^\w\s]', '', question_text).lower().strip()
                            normalized = re.sub(r'\s+', ' ', normalized)
                            if options_dict and isinstance(options_dict, dict):
                                opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options_dict.items()))
                                normalized = f"{normalized}||{opts_str}"
                            text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                            if Question.objects.filter(text_hash=text_hash).exists():
                                duplicates_skipped += 1
                                continue

                            if not dry_run:
                                q_obj = Question.objects.create(
                                    text=question_text,
                                    options=options_dict,
                                    correct_answer=correct_answer,
                                    topic=topic_obj,
                                    sub_topic="PSC Repeated",
                                    difficulty='medium',
                                    language='ml' if re.search(r'[\u0d00-\u0d7f]', question_text) else 'en',
                                    source='psc_official',
                                    status='approved',
                                    is_verified=True,
                                    verified=True,
                                    text_hash=text_hash
                                )
                                q_obj.exams.set([general_psc_exam])
                            else:
                                safe_q = question_text[:50].encode('ascii', errors='replace').decode('ascii')
                                safe_ans = str(options_dict.get(correct_answer, ''))[:30].encode('ascii', errors='replace').decode('ascii')
                                self.stdout.write(f"    [DRY RUN] Q: {safe_q}... | Ans {correct_answer}: {safe_ans}")

                            questions_imported += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error saving questions: {e}"))
                    errors_count += 1

            self.stdout.write(self.style.SUCCESS(
                f"\nIngestion Complete!\n"
                f"  - Questions imported: {questions_imported}\n"
                f"  - Duplicates skipped: {duplicates_skipped}\n"
                f"  - Errors encountered: {errors_count}"
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching feed: {e}"))
