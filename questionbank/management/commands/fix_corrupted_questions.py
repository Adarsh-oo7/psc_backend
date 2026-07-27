import re
import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from questionbank.models import Question

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Fix corrupted questions with embedded options in question_text or mismatched option JSON fields"

    def add_arguments(self, parser):
        parser.add_argument('--use-ai', action='store_true', help='Use Gemini AI API for deep option reconstruction')
        parser.add_argument('--limit', type=int, default=1000, help='Max questions to process')

    def handle(self, *args, **options):
        use_ai = options.get('use_ai', False)
        limit = options.get('limit', 1000)

        self.stdout.write(self.style.NOTICE("Starting question cleanup script..."))

        # Pattern matching embedded options: [a] ... [b] ... [c] ... [d] ... or (a) ... A) ...
        embedded_pattern = re.compile(
            r'^(?P<qtext>.*?)\s*(?:\[|\(|\b)a[.\)\]]\s*(?P<optA>.*?)\s*(?:\[|\(|\b)b[.\)\]]\s*(?P<optB>.*?)\s*(?:\[|\(|\b)c[.\)\]]\s*(?P<optC>.*?)\s*(?:\[|\(|\b)d[.\)\]]\s*(?P<optD>.*)$',
            re.IGNORECASE | re.DOTALL
        )

        questions = Question.objects.all()[:limit]
        regex_fixed = 0
        cleaned_options_count = 0
        ai_fixed = 0

        genai_model = None
        if use_ai:
            try:
                import google.generativeai as genai
                api_key = getattr(settings, 'GEMINI_API_KEY', None)
                if api_key:
                    genai.configure(api_key=api_key)
                    genai_model = genai.GenerativeModel('gemini-2.5-flash')
                    self.stdout.write(self.style.SUCCESS("Gemini AI API configured successfully."))
                else:
                    self.stdout.write(self.style.WARNING("GEMINI_API_KEY not set. Skipping AI phase."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to initialize Gemini AI: {e}"))

        for q in questions:
            modified = False
            q_text = q.text or ""
            opts = q.options or {}

            # Phase 1: Check for embedded [a] [b] [c] [d] options in question_text
            match = embedded_pattern.search(q_text)
            if match:
                extracted_qtext = match.group('qtext').strip()
                opt_a = match.group('optA').strip()
                opt_b = match.group('optB').strip()
                opt_c = match.group('optC').strip()
                opt_d = match.group('optD').strip()

                # Clean any trailing prefixes like [a], [b], [c], [d] inside option values
                clean_opt = lambda s: re.sub(r'^(?:\[|\(|\b)[a-d][.\)\]]\s*', '', s, flags=re.IGNORECASE).strip()

                q.text = extracted_qtext
                q.options = {
                    "A": clean_opt(opt_a),
                    "B": clean_opt(opt_b),
                    "C": clean_opt(opt_c),
                    "D": clean_opt(opt_d)
                }
                modified = True
                regex_fixed += 1

            # Phase 2: Clean leftover [a], [b], [c], [d] prefixes from existing options
            if isinstance(q.options, dict):
                new_opts = {}
                opts_modified = False
                for key in ['A', 'B', 'C', 'D']:
                    val = str(opts.get(key, '')).strip()
                    cleaned_val = re.sub(r'^(?:\[|\(|\b)[a-d][.\)\]]\s*', '', val, flags=re.IGNORECASE).strip()
                    if cleaned_val != val:
                        opts_modified = True
                    new_opts[key] = cleaned_val

                if opts_modified:
                    q.options = new_opts
                    modified = True
                    cleaned_options_count += 1

            # Phase 3: Gemini AI API reconstruction for severely mismatched/corrupted options
            if use_ai and genai_model and (modified or self._is_mismatched(q)):
                try:
                    ai_result = self._repair_with_gemini(genai_model, q)
                    if ai_result:
                        q.text = ai_result.get('text', q.text)
                        q.options = ai_result.get('options', q.options)
                        if ai_result.get('correct_answer') in ['A', 'B', 'C', 'D']:
                            q.correct_answer = ai_result.get('correct_answer')
                        if ai_result.get('explanation'):
                            q.explanation = ai_result.get('explanation')
                        modified = True
                        ai_fixed += 1
                except Exception as err:
                    logger.warning(f"AI repair failed for Question ID {q.id}: {err}")

            if modified:
                q.save()

        self.stdout.write(self.style.SUCCESS(
            f"Finished cleanup! Fixed {regex_fixed} embedded option questions, "
            f"cleaned {cleaned_options_count} option prefixes, and repaired {ai_fixed} with Gemini AI."
        ))

    def _is_mismatched(self, q):
        # Helper to detect if question text and options language/content are severely mismatched
        opts = q.options or {}
        if not isinstance(opts, dict) or len(opts) < 4:
            return True
        # Check if options contain raw bracket strings like '[c]'
        for v in opts.values():
            if str(v).startswith('[') or str(v).startswith('('):
                return True
        return False

    def _repair_with_gemini(self, model, q):
        prompt = f"""You are a Kerala PSC Exam Content Expert.
Clean up and fix this multiple-choice question.

Question: {q.text}
Current Options: {json.dumps(q.options, ensure_ascii=False)}
Current Correct Answer: {q.correct_answer}

Fix any formatting issues, remove embedded [a], [b], [c], [d] from question text, ensure all 4 options A, B, C, D match the question subject accurately, and state the correct answer letter.

Return ONLY a valid JSON object matching this schema:
{{
  "text": "Clean question text",
  "options": {{
    "A": "Option A text",
    "B": "Option B text",
    "C": "Option C text",
    "D": "Option D text"
  }},
  "correct_answer": "A",
  "explanation": "Brief explanation"
}}
"""
        response = model.generate_content(prompt)
        text_resp = response.text.strip()
        # Remove ```json markdown blocks if present
        if text_resp.startswith("```"):
            text_resp = re.sub(r'^```(?:json)?\s*', '', text_resp)
            text_resp = re.sub(r'\s*```$', '', text_resp)
        return json.loads(text_resp)
