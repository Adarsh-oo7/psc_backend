import os
import csv
import json
import hashlib
import re
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from questionbank.models import Question, Topic, Exam

class Command(BaseCommand):
    help = "Bulk imports questions from a pipe-separated CSV or JSON file"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help="Path to CSV or JSON file")
        parser.add_argument('--source', type=str, default='manual', choices=['psc_official', 'rank_file', 'ai_generated', 'community', 'manual'], help="Source of the questions")
        parser.add_argument('--dry-run', action='store_true', help="Execute dry-run without writing to database")

    def handle(self, *args, **options):
        file_path = options['file_path']
        source = options['source']
        dry_run = options['dry_run']

        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        imported_count = 0
        duplicate_count = 0
        error_count = 0

        # Read the file
        questions_data = []
        is_json = file_path.lower().endswith('.json')

        try:
            if is_json:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    questions_data = json.load(f)
            else:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f, delimiter='|')
                    for row in reader:
                        questions_data.append(row)
        except Exception as e:
            raise CommandError(f"Failed to read file: {e}")

        self.stdout.write(f"Parsed {len(questions_data)} records. Starting import...")

        try:
            with transaction.atomic():
                for index, item in enumerate(questions_data, start=1):
                    try:
                        # Extract fields
                        text = item.get('question_text') or item.get('question')
                        option_a = item.get('option_a')
                        option_b = item.get('option_b')
                        option_c = item.get('option_c') or ''
                        option_d = item.get('option_d') or ''
                        correct_answer = item.get('correct_answer') or item.get('correct')
                        topic_name = item.get('topic_name') or item.get('topic') or 'General'
                        exam_name = item.get('exam_name') or item.get('exam')
                        year_val = item.get('year')
                        difficulty = item.get('difficulty') or 'medium'
                        explanation = item.get('explanation') or ''
                        language = item.get('language') or 'en'

                        if not text or not option_a or not option_b or not correct_answer:
                            self.stdout.write(self.style.WARNING(f"Row {index}: Missing required fields (text, option_a, option_b, or correct_answer). Skipping."))
                            error_count += 1
                            continue

                        # Map option strings to options dict format
                        options_dict = {
                            'A': option_a,
                            'B': option_b,
                            'C': option_c,
                            'D': option_d
                        }

                        # Normalization for deduplication
                        normalized = re.sub(r'[^\w\s]', '', text).lower().strip()
                        normalized = re.sub(r'\s+', ' ', normalized)
                        if options_dict and isinstance(options_dict, dict):
                            opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options_dict.items()))
                            normalized = f"{normalized}||{opts_str}"
                        text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                        # Check exact hash match
                        if Question.objects.filter(text_hash=text_hash).exists():
                            duplicate_count += 1
                            continue

                        # Parse year
                        parsed_year = None
                        if year_val:
                            try:
                                year_digits = re.sub(r'\D', '', str(year_val))
                                if year_digits:
                                    parsed_year = int(year_digits)
                            except ValueError:
                                pass

                        # Create related topic and exam
                        topic = None
                        if topic_name:
                            topic_slug = slugify(topic_name)
                            if not dry_run:
                                topic, _ = Topic.objects.get_or_create(
                                    slug=topic_slug,
                                    defaults={'name': topic_name}
                                )
                            else:
                                topic = Topic(name=topic_name, slug=topic_slug)

                        # Create related exam
                        exam_obj = None
                        if exam_name:
                            exam_slug = slugify(exam_name)
                            if not dry_run:
                                from questionbank.models import ExamCategory
                                default_cat, _ = ExamCategory.objects.get_or_create(
                                    name="PSC Direct Recruitment", defaults={'order': 0}
                                )
                                exam_obj, _ = Exam.objects.get_or_create(
                                    slug=exam_slug,
                                    defaults={
                                        'name': exam_name,
                                        'category': default_cat,
                                        'duration_minutes': 75,
                                        'year': parsed_year or 2024
                                    }
                                )
                            else:
                                exam_obj = Exam(name=exam_name, slug=exam_slug)

                        if not dry_run:
                            q = Question(
                                text=text,
                                options=options_dict,
                                correct_answer=correct_answer,
                                topic=topic,
                                difficulty=difficulty,
                                explanation=explanation,
                                language=language,
                                year=parsed_year,
                                source=source,
                                text_hash=text_hash,
                                status='approved'
                            )
                            q.save()
                            if exam_obj:
                                q.exams.add(exam_obj)
                        else:
                            self.stdout.write(f"[DRY RUN] Would import: {text[:50]} | Topic: {topic_name} | Exam: {exam_name}")

                        imported_count += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Row {index}: Error saving question: {e}"))
                        error_count += 1

                if dry_run:
                    raise Exception("Dry run rollback")
        except Exception as e:
            if str(e) != "Dry run rollback":
                raise e

        self.stdout.write(self.style.SUCCESS(
            f"✅ Imported: {imported_count} | ⏭️ Duplicates skipped: {duplicate_count} | ❌ Errors: {error_count}"
        ))
