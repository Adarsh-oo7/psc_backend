"""Find MCQs whose A–D choices are from different questions, then unpublish or rebuild them."""
from __future__ import annotations

import json
import re
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from questionbank.kpsc_format import (
    LETTERS,
    apply_to_question,
    normalize_correct_answer,
    normalize_options,
    repair_known_unrelated_question,
    unrelated_option_bank,
)
from questionbank.models import Question


WHO_RE = re.compile(
    r'(?:^\s*who\b|\bwho\s+(?:is|was|were|appoints|appointed)|ആരാണ്|ആരായിരുന്നു)',
    re.I,
)


def _is_jpsc_appoint_stem(text: str) -> bool:
    stem = (text or '').lower()
    return 'joint public service commission' in stem and 'appoint' in stem


class Command(BaseCommand):
    help = (
        "Detect shuffled/unrelated option banks (person vs procedure vs office), "
        "unpublish them, and optionally rebuild WHO-questions with Gemini."
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write unpublished/rebuilt rows')
        parser.add_argument('--ai', action='store_true', help='Rebuild WHO questions with Gemini')
        parser.add_argument('--limit', type=int, default=80, help='Max AI rebuilds')
        parser.add_argument('--question-id', type=int, default=0)

    def handle(self, *args, **options):
        apply = options['apply']
        use_ai = options['ai']
        limit = options['limit']
        qid = options['question_id']

        qs = Question.objects.filter(status='approved')
        if qid:
            qs = qs.filter(pk=qid)

        stats = {
            'scanned': 0, 'unrelated': 0, 'unpublished': 0,
            'rebuilt': 0, 'known_fix': 0, 'failed': 0,
        }
        samples = []
        to_fix = []

        for q in qs.iterator(chunk_size=400):
            stats['scanned'] += 1
            opts = normalize_options(q.options)
            if not unrelated_option_bank(q.text, opts) and not _is_jpsc_appoint_stem(q.text):
                continue
            stats['unrelated'] += 1
            to_fix.append(q.id)
            if len(samples) < 12:
                samples.append((q.id, (q.text or '')[:90], dict(opts), q.correct_answer, q.is_public))

        self.stdout.write(self.style.NOTICE(
            f"scanned={stats['scanned']} unrelated={stats['unrelated']}"
        ))
        for item in samples:
            self.stdout.write(f"  id={item[0]} public={item[4]} ans={item[3]} {item[1]}")
            self.stdout.write(f"    {item[2]}")

        if not apply:
            self.stdout.write(self.style.WARNING('Dry run. Pass --apply to unpublish / rebuild.'))
            return

        rebuilt_ids = set()
        for q in Question.objects.filter(id__in=to_fix):
            if repair_known_unrelated_question(q):
                apply_to_question(q)
                q.is_public = True
                q.save()
                stats['known_fix'] += 1
                rebuilt_ids.add(q.id)
                self.stdout.write(self.style.SUCCESS(f'known-fix id={q.id}'))

        model = None
        if use_ai:
            model = self._gemini()

        if use_ai and model:
            who_qs = []
            for q in Question.objects.filter(id__in=to_fix).exclude(id__in=rebuilt_ids):
                if WHO_RE.search(q.text or ''):
                    who_qs.append(q)
                if len(who_qs) >= limit:
                    break
            for q in who_qs:
                if self._rebuild_with_ai(q, model):
                    stats['rebuilt'] += 1
                    rebuilt_ids.add(q.id)
                else:
                    stats['failed'] += 1
                time.sleep(2)

        remaining = [i for i in to_fix if i not in rebuilt_ids]
        updated = Question.objects.filter(id__in=remaining, is_public=True).update(is_public=False)
        stats['unpublished'] = updated
        self.stdout.write(self.style.SUCCESS(
            f"known_fix={stats['known_fix']} rebuilt={stats['rebuilt']} "
            f"unpublished={stats['unpublished']} failed={stats['failed']}"
        ))

    def _gemini(self):
        import os
        try:
            import google.generativeai as genai
        except Exception as exc:
            self.stderr.write(f'Gemini import failed: {exc}')
            return None
        api_key = (
            os.environ.get('GEMINI_API_KEY')
            or os.environ.get('GOOGLE_API_KEY')
            or getattr(settings, 'GEMINI_API_KEY', None)
        )
        if not api_key:
            env_file = '/var/www/kpsc-backend/.env'
            if os.path.exists(env_file):
                with open(env_file) as handle:
                    for line in handle:
                        if line.startswith('GEMINI_API_KEY=') or line.startswith('GOOGLE_API_KEY='):
                            api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            break
        if not api_key:
            self.stderr.write('GEMINI_API_KEY missing')
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.5-flash')

    def _rebuild_with_ai(self, question, model) -> bool:
        lang = 'Malayalam' if re.search(r'[\u0D00-\u0D7F]', question.text or '') else 'English'
        prompt = f"""You are a Kerala PSC question editor.
The options below are shuffled from OTHER questions and do not belong with this stem.
Write four PSC-style choices that are ALL the same type of answer the stem is asking for.

Question: {question.text}
Language: {lang}
Broken options: {json.dumps(normalize_options(question.options), ensure_ascii=False)}

Rules:
- Exactly four options A–D in {lang}
- One strictly correct answer
- The other three must be realistic same-domain distractors (same type: all offices, or all people, or all years)
- Do not mix a person's name with a parliamentary procedure or a random adjective

Return ONLY JSON:
{{"options": {{"A": "", "B": "", "C": "", "D": ""}}, "correct_answer": "A", "explanation": ""}}
"""
        try:
            response = model.generate_content(prompt)
            text = (response.text or '').strip()
            if text.startswith('```'):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            data = json.loads(text)
            opts = normalize_options(data.get('options'))
            answer = normalize_correct_answer(data.get('correct_answer'), opts)
            if answer not in LETTERS or unrelated_option_bank(question.text, opts):
                return False
            question.options = opts
            question.correct_answer = answer
            if data.get('explanation'):
                question.explanation = str(data['explanation']).strip()
            question.is_public = True
            apply_to_question(question)
            question.save()
            self.stdout.write(self.style.SUCCESS(f'rebuilt id={question.id}'))
            return True
        except Exception as exc:
            self.stderr.write(f'id={question.id} rebuild failed: {exc}')
            return False
