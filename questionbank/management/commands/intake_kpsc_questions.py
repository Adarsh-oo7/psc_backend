"""Add a small batch of syllabus questions, and hold current affairs for review.

The daily timer and the admin action both call this. It refuses to run when
Gemini intake is switched off, skips stems already in the bank, and drops
any item that fails the same option check as a hand-written question.
"""
from __future__ import annotations

import re
from datetime import date

from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from questionbank.gemini_pool import generate_json, load_keys, probe, record
from questionbank.kpsc_format import servability_issues
from questionbank.models import CurrentAffairs, Exam, GeminiIntakeSettings, Question, Topic
from questionbank.priority_exams import PRIORITY_SLUGS
from questionbank.syllabus_db import SYLLABUS_DATABASE, resolve_exam_slug


class Command(BaseCommand):
    help = "Fill thin syllabus sections from Gemini, without duplicating questions"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Run even when intake is switched off")
        parser.add_argument("--probe", action="store_true", help="Only check that the project keys respond")
        parser.add_argument("--skip-affairs", action="store_true")

    def handle(self, *args, **options):
        if options["probe"]:
            for line in probe():
                self.stdout.write(line)
            return

        settings = GeminiIntakeSettings.load()
        if not settings.enabled and not options["force"]:
            self.stdout.write("Gemini intake is off. Turn it on in Admin → Gemini intake.")
            return
        if not load_keys():
            self.stdout.write("No Gemini keys are configured.")
            return

        from questionbank.models import GeminiProjectUsage
        accepted = sum(
            row.accepted
            for row in GeminiProjectUsage.objects.filter(day=timezone.localdate())
        )
        report = [f"Started with {accepted} questions already kept today."]
        calls = 0
        for topic_name, exams in self._thin_topics():
            if accepted >= settings.daily_accept_cap or calls >= settings.max_calls_per_run:
                break
            ask = min(settings.questions_per_request, settings.daily_accept_cap - accepted)
            if ask < 1:
                break
            try:
                payload, project = generate_json(self._question_prompt(topic_name, exams, ask), settings)
            except RuntimeError as exc:
                report.append(f"{topic_name}: {exc}")
                break
            calls += 1
            rows = payload if isinstance(payload, list) else payload.get("questions", [])
            kept = rejected = duplicates = 0
            for item in rows:
                result = self._save_question(item, topic_name, exams, settings.hold_for_review)
                if result == "kept":
                    kept += 1
                elif result == "duplicate":
                    duplicates += 1
                else:
                    rejected += 1
            record(project, accepted=kept, rejected=rejected, duplicates=duplicates)
            accepted += kept
            report.append(
                f"{topic_name}: kept {kept}, rejected {rejected}, duplicates {duplicates} (project {project})"
            )

        if settings.run_current_affairs and not options["skip_affairs"] and calls < settings.max_calls_per_run:
            report.append(self._current_affairs(settings))

        settings.last_run_at = timezone.now()
        settings.last_report = "\n".join(report)[:4000]
        settings.save(update_fields=["last_run_at", "last_report"])
        self.stdout.write(settings.last_report)

    def _thin_topics(self):
        """Syllabus titles that still have fewer public questions than the paper's marks."""
        queue = []
        for slug in PRIORITY_SLUGS:
            exam = Exam.objects.filter(slug=slug).first()
            key = resolve_exam_slug(slug)
            rows = (SYLLABUS_DATABASE.get(key) or {}).get("syllabus") or []
            if not exam or not rows:
                continue
            for row in rows:
                topic_name = row.get("topic") or ""
                marks = int(row.get("marks") or 0)
                target = max(8, min(20, marks))
                have = exam.questions.filter(is_public=True, status="approved").filter(
                    Q(topic__name__iexact=topic_name) | Q(sub_topic__iexact=topic_name)
                ).count()
                if have >= target:
                    continue
                queue.append((have, topic_name, exam))
        queue.sort(key=lambda item: item[0])
        grouped = {}
        for _have, topic_name, exam in queue:
            grouped.setdefault(topic_name, [])
            if exam not in grouped[topic_name]:
                grouped[topic_name].append(exam)
        return list(grouped.items())

    def _question_prompt(self, topic_name, exams, count):
        exam_names = ", ".join(exam.name for exam in exams[:4])
        return f"""You write Kerala PSC multiple-choice questions for this syllabus section only.

Section: {topic_name}
Exams: {exam_names}
Write {count} questions.

Rules:
- Facts a Kerala PSC candidate is expected to know for this section.
- One stem, exactly four options, one correct letter.
- All four options must be the same kind of answer (all names, or all places, or all short phrases).
- Do not use "all of the above" or "none of these".
- Do not mix an unrelated subject into the options.
- If you are not sure a fact is true, skip that question.
- Do not repeat a question you have seen in standard PSC banks word for word if you can write a fresh stem.
- English only.

Return ONLY a JSON array:
[{{"text":"...","options":{{"A":"...","B":"...","C":"...","D":"..."}},"correct_answer":"A","explanation":"one sentence"}}]
"""

    def _save_question(self, item, topic_name, exams, hold):
        if not isinstance(item, dict):
            return "rejected"
        text = str(item.get("text") or item.get("question") or "").strip()
        options = item.get("options") or {}
        if isinstance(options, list):
            options = {letter: str(options[i]) for i, letter in enumerate("ABCD") if i < len(options)}
        options = {letter: str(options.get(letter) or options.get(letter.lower()) or "").strip() for letter in "ABCD"}
        answer = str(item.get("correct_answer") or item.get("correct") or "").strip().upper()[:1]
        explanation = str(item.get("explanation") or "").strip()
        if servability_issues(text, options, answer):
            return "rejected"
        if Question.objects.filter(text__iexact=text).exists():
            return "duplicate"
        topic = Topic.objects.filter(name__iexact=topic_name).first()
        if topic is None:
            topic, _ = Topic.objects.get_or_create(
                slug=slugify(topic_name)[:150] or "topic",
                defaults={"name": topic_name},
            )
        question = Question(
            topic=topic,
            sub_topic=topic_name[:255],
            text=text,
            options=options,
            correct_answer=answer,
            explanation=explanation,
            difficulty="medium",
            language="en",
            source="ai_generated",
            status="pending" if hold else "approved",
            is_public=not hold,
            is_verified=not hold,
            verified=not hold,
            tags=["syllabus-2026", "gemini-intake", topic_name],
        )
        try:
            question.save()
        except IntegrityError:
            return "duplicate"
        if not question.is_public and not hold:
            question.delete()
            return "rejected"
        question.exams.add(*exams)
        return "kept"

    def _current_affairs(self, settings):
        today = date.today().isoformat()
        prompt = f"""List Kerala PSC current affairs for {today}.

Include only items you are confident really happened in the last 7 days, about Kerala or India
(government, schemes, appointments, awards, sports, science). If you are not sure, return fewer items.
Do not invent names, numbers, or dates. 4 to 8 items.

Return ONLY JSON:
{{"items":[{{"category":"kerala","headline":"...","summary":"...","mcq":{{"question":"...","options":["","","",""],"correct_index":0,"explanation":"..."}}}}]}}
category is one of kerala, india, international, science, economy, sports.
"""
        try:
            payload, project = generate_json(prompt, settings)
        except RuntimeError as exc:
            return f"Current affairs: {exc}"
        items = payload.get("items", []) if isinstance(payload, dict) else []
        kept = duplicates = 0
        for item in items:
            headline = re.sub(r"\s+", " ", str(item.get("headline") or "")).strip()
            if len(headline) < 12:
                continue
            if CurrentAffairs.objects.filter(title__iexact=headline).exists():
                duplicates += 1
                continue
            summary = str(item.get("summary") or "").strip()
            mcq = item.get("mcq") if isinstance(item.get("mcq"), dict) else {}
            CurrentAffairs.objects.create(
                title=headline[:255],
                content=summary or headline,
                category=str(item.get("category") or "india")[:50],
                publication_date=timezone.localdate(),
                psc_likelihood="medium",
                ai_summary=summary,
                mcq=mcq,
                is_published=False,
            )
            kept += 1
        record(project, accepted=kept, duplicates=duplicates)
        return f"Current affairs held for review: {kept}, duplicates {duplicates} (project {project})"
