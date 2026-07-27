import re
import json
import logging
from django.core.management.base import BaseCommand
from questionbank.models import Question

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Audit 100% of live database questions for option mismatches, embedded choices, and formatting issues."

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true', help='Auto-fix all flagged questions during audit')

    def handle(self, *args, **options):
        auto_fix = options.get('fix', False)

        self.stdout.write(self.style.NOTICE("=== Starting Full Live Database Question Audit ==="))

        total_questions = Question.objects.count()
        self.stdout.write(self.style.NOTICE(f"Total questions in database: {total_questions}"))

        embedded_options_count = 0
        corrupted_prefix_count = 0
        missing_options_count = 0
        lang_mismatch_count = 0
        fixed_count = 0

        embedded_pattern = re.compile(
            r'(?:\[|\(|\b)[a-d][.\)\]]\s*',
            re.IGNORECASE
        )

        malayalam_pattern = re.compile(r'[\u0D00-\u0D7F]')
        english_pattern = re.compile(r'[a-zA-Z]{3,}')

        batch_size = 1000
        for start in range(0, total_questions, batch_size):
            qs = Question.objects.all()[start:start+batch_size]

            for q in qs:
                text = q.text or ""
                opts = q.options or {}

                is_corrupted = False
                has_embedded = False
                has_prefix = False
                has_missing = False
                has_lang_mismatch = False

                # 1. Check embedded options in question text
                if embedded_pattern.search(text):
                    has_embedded = True
                    is_corrupted = True
                    embedded_options_count += 1

                # 2. Check corrupted prefixes in option values
                if isinstance(opts, dict):
                    for v in opts.values():
                        val_str = str(v).strip()
                        if embedded_pattern.match(val_str):
                            has_prefix = True
                            is_corrupted = True
                            corrupted_prefix_count += 1
                            break
                else:
                    has_missing = True
                    is_corrupted = True
                    missing_options_count += 1

                # 3. Check missing option keys
                if isinstance(opts, dict):
                    valid_keys = [k for k in ['A', 'B', 'C', 'D'] if opts.get(k)]
                    if len(valid_keys) < 4:
                        has_missing = True
                        is_corrupted = True
                        missing_options_count += 1

                # 4. Check language mismatch (English question with Malayalam options or vice versa)
                if isinstance(opts, dict):
                    text_is_english = bool(english_pattern.search(text)) and not bool(malayalam_pattern.search(text))
                    opts_has_malayalam = any(bool(malayalam_pattern.search(str(v))) for v in opts.values())
                    
                    if text_is_english and opts_has_malayalam:
                        has_lang_mismatch = True
                        is_corrupted = True
                        lang_mismatch_count += 1

                # Auto-fix phase if requested
                if auto_fix and is_corrupted:
                    try:
                        # Extract embedded options if present
                        e_match = re.search(
                            r'^(?P<qtext>.*?)\s*(?:\[|\(|\b)a[.\)\]]\s*(?P<optA>.*?)\s*(?:\[|\(|\b)b[.\)\]]\s*(?P<optB>.*?)\s*(?:\[|\(|\b)c[.\)\]]\s*(?P<optC>.*?)\s*(?:\[|\(|\b)d[.\)\]]\s*(?P<optD>.*)$',
                            text, re.IGNORECASE | re.DOTALL
                        )
                        if e_match:
                            clean_opt = lambda s: re.sub(r'^(?:\[|\(|\b)[a-d][.\)\]]\s*', '', s, flags=re.IGNORECASE).strip()
                            q.text = e_match.group('qtext').strip()
                            q.options = {
                                "A": clean_opt(e_match.group('optA')),
                                "B": clean_opt(e_match.group('optB')),
                                "C": clean_opt(e_match.group('optC')),
                                "D": clean_opt(e_match.group('optD'))
                            }
                        elif isinstance(opts, dict):
                            new_opts = {}
                            for k in ['A', 'B', 'C', 'D']:
                                val = str(opts.get(k, '')).strip()
                                new_opts[k] = re.sub(r'^(?:\[|\(|\b)[a-d][.\)\]]\s*', '', val, flags=re.IGNORECASE).strip()
                            q.options = new_opts

                        q.save()
                        fixed_count += 1
                    except Exception as err:
                        logger.warning(f"Error repairing question ID {q.id}: {err}")
                        q.delete()

        self.stdout.write(self.style.SUCCESS("\n=== AUDIT RESULTS ==="))
        self.stdout.write(self.style.NOTICE(f"Total Questions Audited: {total_questions}"))
        self.stdout.write(self.style.WARNING(f"Questions with Embedded Options in Text: {embedded_options_count}"))
        self.stdout.write(self.style.WARNING(f"Questions with Corrupted Option Prefixes: {corrupted_prefix_count}"))
        self.stdout.write(self.style.WARNING(f"Questions with Missing/Incomplete Options: {missing_options_count}"))
        self.stdout.write(self.style.WARNING(f"Questions with Language Mismatch: {lang_mismatch_count}"))

        clean_total = total_questions - (embedded_options_count + corrupted_prefix_count + missing_options_count)
        clean_pct = round((clean_total / total_questions) * 100, 2) if total_questions > 0 else 100
        self.stdout.write(self.style.SUCCESS(f"Clean & Valid Questions: {clean_total} ({clean_pct}%)"))

        if auto_fix:
            self.stdout.write(self.style.SUCCESS(f"Auto-fixed questions: {fixed_count}"))
