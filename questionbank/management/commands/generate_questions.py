import os
import json
import time
import re
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.conf import settings
from django.utils.text import slugify
from questionbank.models import Question, Topic, Exam

class Command(BaseCommand):
    help = "Finds topics with fewer than target questions and generates questions using Gemini API"

    def add_arguments(self, parser):
        parser.add_argument('--min-count', type=int, default=50, help="Minimum questions count threshold")
        parser.add_argument('--per-topic', type=int, default=20, help="Questions to generate per topic")
        parser.add_argument('--exam', type=str, help="Associate generated questions with this exam name")
        parser.add_argument('--topic', type=str, help="Generate questions for this specific topic name only")
        parser.add_argument('--count', type=int, default=30, help="Count of questions to generate when --topic is specified")
        parser.add_argument('--language', type=str, default='en', choices=['en', 'ml'], help="Language for generated questions")
        parser.add_argument('--approve-all', action='store_true', help="Set generated questions directly to approved status")

    def handle(self, *args, **options):
        # API Key Setup
        api_key = os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise CommandError("GEMINI_API_KEY not found. Please set the environment variable or add it to settings.py")

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
        except ImportError:
            raise CommandError("google-generativeai is not installed. Please install it using: pip install google-generativeai")

        min_count = options['min_count']
        per_topic = options['per_topic']
        exam_name = options['exam']
        specific_topic_name = options['topic']
        specific_count = options['count']
        language = options['language']
        approve_all = options['approve-all']

        status_val = 'approved' if approve_all else 'pending'

        # Load exam if specified
        exam_obj = None
        if exam_name:
            exam_slug = slugify(exam_name)
            # Fetch default category
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
                    'year': 2024
                }
            )

        # Build list of topics to generate for
        topics_to_process = []
        if specific_topic_name:
            topic, _ = Topic.objects.get_or_create(
                slug=slugify(specific_topic_name),
                defaults={'name': specific_topic_name}
            )
            topics_to_process.append((topic, specific_count))
        else:
            # Query topics with fewer than min_count questions
            # Count questions under questions_topic relationship
            topics_with_counts = Topic.objects.annotate(
                q_count=Count('questions_topic')
            ).filter(q_count__lt=min_count)

            for t in topics_with_counts:
                topics_to_process.append((t, per_topic))

        if not topics_to_process:
            self.stdout.write(self.style.SUCCESS("All topics have sufficient questions! No work to do."))
            return

        self.stdout.write(f"Identified {len(topics_to_process)} topics to process.")

        # Instantiate Gemini model
        model = genai.GenerativeModel('gemini-2.5-flash')

        for topic, count_needed in topics_to_process:
            self.stdout.write(f"Generating {count_needed} questions for topic: {topic.name}...")
            
            prompt = f"""
You are a Kerala PSC exam question setter with 15 years of experience.
Generate {count_needed} multiple choice questions about: {topic.name}

Strict rules:
- Questions must be factual, verifiable facts only
- Based on actual Kerala PSC LDC/Degree Level exam pattern
- All 4 options must be plausible (not obviously wrong)
- Cover different difficulty levels: 40% easy, 40% medium, 20% hard
- Include year/date facts where relevant
- No duplicate questions
- Questions in {language} language

Return ONLY valid JSON array, no other text:
[
  {{
    "question": "question text here",
    "option_a": "option 1",
    "option_b": "option 2",
    "option_c": "option 3",
    "option_d": "option 4",
    "correct": "A",
    "explanation": "Brief explanation why this answer is correct (max 2 sentences)",
    "difficulty": "easy|medium|hard"
  }}
]
"""

            try:
                # Call Gemini API with JSON output enforcement
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # Parse JSON
                raw_json = response.text.strip()
                # Clean up any trailing text markdown if Gemini slipped up
                if raw_json.startswith('```json'):
                    raw_json = raw_json[7:-3].strip()
                elif raw_json.startswith('```'):
                    raw_json = raw_json[3:-3].strip()

                questions_list = json.loads(raw_json)
                self.stdout.write(f"Successfully received {len(questions_list)} questions from Gemini API.")

                success_count = 0
                dup_count = 0

                for item in questions_list:
                    q_text = item.get('question')
                    opt_a = item.get('option_a')
                    opt_b = item.get('option_b')
                    opt_c = item.get('option_c') or ''
                    opt_d = item.get('option_d') or ''
                    correct = item.get('correct')
                    explanation = item.get('explanation') or ''
                    difficulty = item.get('difficulty') or 'medium'

                    if not q_text or not opt_a or not opt_b or not correct:
                        continue

                    # Structure options into JSONField format
                    options_dict = {
                        'A': opt_a,
                        'B': opt_b,
                        'C': opt_c,
                        'D': opt_d
                    }

                    # Determine and normalize hash
                    normalized = re.sub(r'[^\w\s]', '', q_text).lower().strip()
                    normalized = re.sub(r'\s+', ' ', normalized)
                    if options_dict and isinstance(options_dict, dict):
                        opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options_dict.items()))
                        normalized = f"{normalized}||{opts_str}"
                    import hashlib
                    text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                    # Deduplication check
                    if Question.objects.filter(text_hash=text_hash).exists():
                        dup_count += 1
                        continue

                    # Create question
                    q = Question.objects.create(
                        text=q_text,
                        options=options_dict,
                        correct_answer=correct,
                        topic=topic,
                        difficulty=difficulty,
                        explanation=explanation,
                        language=language,
                        source='ai_generated',
                        verified=approve_all,
                        is_verified=approve_all,
                        status=status_val,
                        text_hash=text_hash
                    )

                    if exam_obj:
                        q.exams.add(exam_obj)

                    success_count += 1

                self.stdout.write(self.style.SUCCESS(
                    f"Saved {success_count} questions. Skipped {dup_count} duplicates."
                ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error generating questions for {topic.name}: {e}"))

            # Rate limit sleep between topics
            self.stdout.write("Rate-limiting pause...")
            time.sleep(2.0)

        self.stdout.write(self.style.SUCCESS("AI Generation session completed successfully!"))
