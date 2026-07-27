import re
import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from questionbank.models import Question

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Find questions with language/domain mismatched options and rebuild 4 clean choices using Gemini AI API."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=500, help='Max questions to repair per run')

    def handle(self, *args, **options):
        limit = options.get('limit', 500)

        self.stdout.write(self.style.NOTICE("=== Starting AI Mismatched Options Repair Script ==="))

        try:
            import os
            import google.generativeai as genai
            api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
            if not api_key:
                # Try reading /var/www/kpsc-backend/.env
                env_file = '/var/www/kpsc-backend/.env'
                if os.path.exists(env_file):
                    with open(env_file) as f:
                        for line in f:
                            if line.startswith('GEMINI_API_KEY='):
                                api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                                break
                            elif line.startswith('GOOGLE_API_KEY='):
                                api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                                break

            if not api_key:
                self.stdout.write(self.style.ERROR("GEMINI_API_KEY not found. Please set environment variable."))
                return

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            self.stdout.write(self.style.SUCCESS("Gemini AI API configured successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to initialize Gemini AI: {e}"))
            return

        malayalam_pattern = re.compile(r'[\u0D00-\u0D7F]')
        english_pattern = re.compile(r'[a-zA-Z]{3,}')

        # Find questions where text is English but options contain Malayalam (or options have unrelated choices)
        corrupted_questions = []
        for q in Question.objects.all():
            text = q.text or ""
            opts = q.options or {}

            if not isinstance(opts, dict) or len(opts) < 4:
                corrupted_questions.append(q)
                continue

            text_is_english = bool(english_pattern.search(text)) and not bool(malayalam_pattern.search(text))
            opts_has_malayalam = any(bool(malayalam_pattern.search(str(v))) for v in opts.values())

            text_is_malayalam = bool(malayalam_pattern.search(text))
            opts_has_english = any(bool(english_pattern.search(str(v))) for v in opts.values() if len(str(v)) > 5)

            if (text_is_english and opts_has_malayalam) or (text_is_malayalam and opts_has_english):
                corrupted_questions.append(q)

            if len(corrupted_questions) >= limit:
                break

        total_found = len(corrupted_questions)
        self.stdout.write(self.style.WARNING(f"Found {total_found} questions with mismatched option language/content."))

        fixed_count = 0
        for i, q in enumerate(corrupted_questions, 1):
            try:
                lang = 'Malayalam' if bool(malayalam_pattern.search(q.text)) else 'English'
                prompt = f"""You are a Senior Kerala PSC Exam Creator.
Below is a Kerala PSC question whose current options are corrupted or language-mismatched.

Question: {q.text}
Language: {lang}
Current Options: {json.dumps(q.options, ensure_ascii=False)}
Current Correct Answer Letter: {q.correct_answer}

Create 4 clean, accurate, domain-relevant multiple-choice options (A, B, C, D) in {lang} language.
Ensure ONE option is the strictly correct answer to the question, and the other 3 are realistic distractors in {lang}.

Return ONLY a JSON object:
{{
  "text": "{q.text}",
  "options": {{
    "A": "Option A text in {lang}",
    "B": "Option B text in {lang}",
    "C": "Option C text in {lang}",
    "D": "Option D text in {lang}"
  }},
  "correct_answer": "A",
  "explanation": "Brief explanation"
}}
"""
                response = model.generate_content(prompt)
                resp_text = response.text.strip()
                if resp_text.startswith("```"):
                    resp_text = re.sub(r'^```(?:json)?\s*', '', resp_text)
                    resp_text = re.sub(r'\s*```$', '', resp_text)

                data = json.loads(resp_text)
                if data.get('options') and isinstance(data['options'], dict) and len(data['options']) == 4:
                    q.text = data.get('text', q.text)
                    q.options = data['options']
                    if data.get('correct_answer') in ['A', 'B', 'C', 'D']:
                        q.correct_answer = data['correct_answer']
                    if data.get('explanation'):
                        q.explanation = data['explanation']
                    q.save()
                    fixed_count += 1
                    self.stdout.write(self.style.SUCCESS(f"[{i}/{total_found}] Repaired Question ID {q.id}: {q.text[:40]}..."))
            except Exception as err:
                self.stdout.write(self.style.ERROR(f"[{i}/{total_found}] Failed to repair Question ID {q.id}: {err}"))

        self.stdout.write(self.style.SUCCESS(f"\nCompleted AI repair! Successfully rebuilt options for {fixed_count} questions."))
