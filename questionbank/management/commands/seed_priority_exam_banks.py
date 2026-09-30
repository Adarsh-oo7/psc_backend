"""Create the 10 high-search Kerala PSC exams, syllabus rows, ~1000 questions, and 10 sets."""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.text import slugify

from questionbank.kpsc_format import is_servable
from questionbank.models import Exam, ExamCategory, ExamSyllabus, ModelExam, Question, Topic
from questionbank.priority_exams import PRIORITY_EXAMS
from questionbank.syllabus_db import SYLLABUS_DATABASE

BANK_SIZE = 1000
SET_COUNT = 10
SET_SIZE = 100


def _find_topics(name: str) -> list[Topic]:
    needle = name.split("—")[0].split(",")[0].strip()
    words = [w for w in needle.replace("/", " ").split() if len(w) > 2]
    qs = Topic.objects.filter(name__iexact=name)
    if qs.exists():
        return list(qs)
    qs = Topic.objects.filter(name__icontains=needle)
    if qs.exists():
        return list(qs[:8])
    if words:
        q_obj = Q()
        for word in words[:3]:
            q_obj |= Q(name__icontains=word)
        qs = Topic.objects.filter(q_obj)
        if qs.exists():
            return list(qs[:8])
    return []


class Command(BaseCommand):
    help = "Seed SEO-priority PSC exams with syllabus, ~1000 questions, and 10 model sets"

    def add_arguments(self, parser):
        parser.add_argument("--exam-slug", type=str, help="Seed only this slug")
        parser.add_argument("--bank-size", type=int, default=BANK_SIZE)

    def handle(self, *args, **options):
        bank_size = options["bank_size"]
        only = (options.get("exam_slug") or "").strip()
        category, _ = ExamCategory.objects.get_or_create(
            name="PSC Direct Recruitment",
            defaults={"description": "Direct recruitment posts", "order": 0},
        )
        category.order = 0
        category.save(update_fields=["order"])

        rows = PRIORITY_EXAMS
        if only:
            rows = [item for item in PRIORITY_EXAMS if item["slug"] == only]
            if not rows:
                self.stderr.write(f"Unknown slug {only}")
                return

        for spec in rows:
            exam = self._upsert_exam(category, spec)
            self._upsert_syllabus_rows(exam, spec)
            attached = self._attach_questions(exam, spec, bank_size)
            sets = self._build_sets(exam)
            self.stdout.write(self.style.SUCCESS(
                f"{spec['rank']}. {exam.slug}: questions={attached} sets={sets}"
            ))

    def _upsert_exam(self, category, spec):
        syllabus = spec["syllabus"]
        pattern = {
            "total_questions": 100,
            "duration_minutes": spec["duration_minutes"],
            "marking_scheme": "+1 / −0.33",
            "sets": SET_COUNT,
            "bank_size": BANK_SIZE,
            "level": spec["level"],
        }
        defaults = {
            "name": spec["name"],
            "year": 2026,
            "category": category,
            "duration_minutes": spec["duration_minutes"],
            "category_number": spec.get("cat_no") or "",
            "official_syllabus": {
                "subjects": [{"title": row["topic"], "marks": row["marks"]} for row in syllabus],
                "opportunity": spec.get("opportunity"),
                "apply_by": spec.get("apply_by"),
            },
            "question_pattern": pattern,
        }
        exam, created = Exam.objects.get_or_create(slug=spec["slug"], defaults=defaults)
        for key, value in defaults.items():
            setattr(exam, key, value)
        exam.save()
        SYLLABUS_DATABASE[spec["slug"]] = {
            "name": spec["name"],
            "cat_no": spec.get("cat_no"),
            "level": spec["level"],
            "duration_minutes": spec["duration_minutes"],
            "total_marks": 100,
            "negative_marking": -0.33,
            "syllabus": syllabus,
        }
        self.stdout.write(("Created" if created else "Updated") + f" exam {exam.slug}")
        return exam

    def _upsert_syllabus_rows(self, exam, spec):
        fallbacks = spec.get("topic_fallbacks") or {}
        for row in spec["syllabus"]:
            topic = Topic.objects.filter(name__iexact=row["topic"]).first()
            if not topic:
                topic, _ = Topic.objects.get_or_create(
                    slug=slugify(row["topic"])[:150],
                    defaults={"name": row["topic"]},
                )
                if topic.name != row["topic"]:
                    topic.name = row["topic"]
                    topic.save(update_fields=["name"])
            ExamSyllabus.objects.update_or_create(
                exam=exam,
                topic=topic,
                defaults={"num_questions": max(5, int(round(row["marks"])))},
            )
            _ = fallbacks  # used in attach

    def _topic_candidates(self, spec, topic_name):
        names = [topic_name] + list((spec.get("topic_fallbacks") or {}).get(topic_name, []))
        found = []
        seen = set()
        for name in names:
            for topic in _find_topics(name):
                if topic.id not in seen:
                    seen.add(topic.id)
                    found.append(topic)
        return found

    def _attach_questions(self, exam, spec, bank_size):
        exam.questions.clear()
        used = set()
        attached = 0
        total_marks = sum(row["marks"] for row in spec["syllabus"]) or 100

        for row in spec["syllabus"]:
            want = max(40, int(round(bank_size * row["marks"] / total_marks)))
            topics = self._topic_candidates(spec, row["topic"])
            if not topics:
                continue
            qs = (
                Question.objects.filter(
                    is_public=True,
                    status="approved",
                    topic__in=topics,
                )
                .exclude(id__in=used)
                .order_by("-times_answered", "id")
            )
            batch = []
            for question in qs.iterator(chunk_size=200):
                if len(batch) >= want:
                    break
                if not is_servable(question.text, question.options, question.correct_answer):
                    continue
                batch.append(question.id)
                used.add(question.id)
            if batch:
                exam.questions.add(*batch)
                attached += len(batch)

        if attached < bank_size:
            extra = (
                Question.objects.filter(is_public=True, status="approved")
                .exclude(id__in=used)
                .order_by("-times_answered", "id")
            )
            fill = []
            for question in extra.iterator(chunk_size=300):
                if attached + len(fill) >= bank_size:
                    break
                if not is_servable(question.text, question.options, question.correct_answer):
                    continue
                fill.append(question.id)
                used.add(question.id)
            if fill:
                exam.questions.add(*fill)
                attached += len(fill)
        return attached

    def _build_sets(self, exam):
        ids = list(exam.questions.values_list("id", flat=True)[: SET_COUNT * SET_SIZE])
        if len(ids) < SET_SIZE:
            return 0
        ModelExam.objects.filter(exam=exam, name__startswith="Set ").delete()
        created = 0
        for index in range(SET_COUNT):
            chunk = ids[index * SET_SIZE : (index + 1) * SET_SIZE]
            if len(chunk) < SET_SIZE:
                break
            paper = ModelExam.objects.create(
                name=f"Set {index + 1} — {exam.name}",
                exam=exam,
                duration_minutes=exam.duration_minutes or 75,
            )
            paper.questions.set(chunk)
            created += 1
        return created
