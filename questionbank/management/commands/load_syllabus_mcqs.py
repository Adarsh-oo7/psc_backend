"""Add syllabus MCQs and rebuild the papers students open, without wiping other banks."""
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.text import slugify

from questionbank.kpsc_format import is_servable, servability_issues
from questionbank.models import Exam, ModelExam, Question, Topic
from questionbank.syllabus_mcqs import SYLLABUS_MCQS

EXAM_TOPICS = {
    "junior-lab-assistant": {
        "Lab Safety and Instruments",
        "Physics",
        "Chemistry",
        "Biology and Public Health",
    },
    "laboratory-attender": {
        "Lab Safety and Instruments",
        "Physics",
        "Chemistry",
        "Biology and Public Health",
    },
    "motor-mechanic": {
        "Engine and Fuel System",
        "Brake Clutch and Transmission",
        "Steering and Suspension",
        "Cooling and Lubrication",
        "Auto Electrical",
    },
    "village-field-assistant": {
        "Vocational Agriculture Topics",
        "Physics",
        "Chemistry",
        "Biology and Public Health",
        "Economics",
        "Important Laws",
        "Arts Culture Literature Sports",
    },
    "fire-and-rescue": {
        "Fire and Rescue Special Topics",
        "Physics",
        "Chemistry",
        "Biology and Public Health",
    },
    "nurse-grade-ii": {
        "Anatomy and Physiology",
        "Fundamentals of Nursing",
        "Community Health and First Aid",
        "Biology and Public Health",
    },
    "lineman": {
        "Basic Electricity",
        "Ohm's Law and Circuits",
        "Overhead Lines and Safety",
        "Transformers and Distribution",
        "Instruments and Earthing",
    },
    "electrician": {
        "Basic Electricity — Fundamentals, Resistance, Conductors, Wires",
        "Ohm's Law — Kirchhoff's Law, Temperature Effects, Cell Types",
        "Magnetism — Properties, Electromagnetism, Fleming's Rules, Faraday's Laws",
        "Alternating Current and Earthing — AC, Earthing, Wiring, Megger",
        "DC Machines — Generators, DC Motors, Starters",
        "AC Motors — Single & 3 Phase, DOL, Star-Delta Starters",
        "Instruments and Transformers — Measuring Instruments, EMF Equation",
        "Illumination and Electronics — Lamps, Semiconductors, Diodes, Transistors",
        "Power Generation — Energy Sources, Types of Power Generation",
        "Transmission and Distribution — AC vs DC Comparison",
    },
    "special-branch-assistant": {"Special Branch and Police Topics"},
    "civil-excise-officer": {"Excise Special Topics"},
    "beat-forest-officer": {"Forest and Wildlife Special Topics"},
    "police-constable-band": {"Band Music and Police Special Topics"},
    "assistant-project-engineer": {
        "Engineering Maths",
        "Physics",
        "Basic Engineering and Drawing",
    },
}

# Counts follow the high-mark syllabus. They add up to 100.
SET_PLANS = {
    "junior-lab-assistant": [
        ("Lab Safety and Instruments", 20),
        ("Physics", 20),
        ("Chemistry", 20),
        ("Biology and Public Health", 20),
        ("Facts About Kerala", 10),
        ("Maths", 10),
    ],
    "motor-mechanic": [
        ("Engine and Fuel System", 20),
        ("Brake Clutch and Transmission", 20),
        ("Steering and Suspension", 10),
        ("Cooling and Lubrication", 10),
        ("Auto Electrical", 15),
        ("Facts About Kerala", 10),
        ("Maths", 10),
        ("English", 5),
    ],
    "village-field-assistant": [
        ("Vocational Agriculture Topics", 20),
        ("History", 5),
        ("Geography", 5),
        ("Economics", 5),
        ("Constitution and Polity", 5),
        ("Facts About Kerala", 5),
        ("Biology and Public Health", 6),
        ("Physics", 3),
        ("Chemistry", 3),
        ("Arts Culture Literature Sports", 5),
        ("Computer", 3),
        ("Important Laws", 5),
        ("Maths", 10),
        ("English", 10),
        ("Malayalam", 10),
    ],
    "laboratory-attender": [
        ("Physics", 15),
        ("Chemistry", 15),
        ("Biology and Public Health", 15),
        ("Lab Safety and Instruments", 15),
        ("Facts About Kerala", 10),
        ("Maths", 10),
        ("English", 10),
        ("Daily Current Affairs", 10),
    ],
    "lineman": [
        ("Basic Electricity", 15),
        ("Ohm's Law and Circuits", 15),
        ("Overhead Lines and Safety", 15),
        ("Transformers and Distribution", 15),
        ("Instruments and Earthing", 10),
        ("Facts About Kerala", 10),
        ("Maths", 10),
        ("English", 10),
    ],
    "electrician": [
        ("Basic Electricity — Fundamentals, Resistance, Conductors, Wires", 10),
        ("Ohm's Law — Kirchhoff's Law, Temperature Effects, Cell Types", 10),
        ("Magnetism — Properties, Electromagnetism, Fleming's Rules, Faraday's Laws", 10),
        ("Alternating Current and Earthing — AC, Earthing, Wiring, Megger", 10),
        ("DC Machines — Generators, DC Motors, Starters", 10),
        ("AC Motors — Single & 3 Phase, DOL, Star-Delta Starters", 10),
        ("Instruments and Transformers — Measuring Instruments, EMF Equation", 10),
        ("Illumination and Electronics — Lamps, Semiconductors, Diodes, Transistors", 10),
        ("Power Generation — Energy Sources, Types of Power Generation", 10),
        ("Transmission and Distribution — AC vs DC Comparison", 10),
    ],
    "nurse-grade-ii": [
        ("Anatomy and Physiology", 20),
        ("Fundamentals of Nursing", 20),
        ("Community Health and First Aid", 15),
        ("Biology and Public Health", 10),
        ("Facts About Kerala", 10),
        ("Daily Current Affairs", 5),
        ("English", 10),
        ("Malayalam", 10),
    ],
    "fire-and-rescue": [
        ("History", 5),
        ("Geography", 5),
        ("Economics", 5),
        ("Constitution and Polity", 8),
        ("Facts About Kerala", 3),
        ("Biology and Public Health", 4),
        ("Physics", 3),
        ("Chemistry", 3),
        ("Arts Culture Literature Sports", 4),
        ("Daily Current Affairs", 10),
        ("Maths", 10),
        ("English", 10),
        ("Malayalam", 10),
        ("Fire and Rescue Special Topics", 20),
    ],
    "special-branch-assistant": [
        ("History", 8),
        ("Geography", 7),
        ("Constitution and Polity", 10),
        ("Facts About Kerala", 8),
        ("Daily Current Affairs", 10),
        ("Maths", 10),
        ("English", 10),
        ("Malayalam", 10),
        ("Science", 7),
        ("Special Branch and Police Topics", 20),
    ],
    "civil-excise-officer": [
        ("History", 8),
        ("Geography", 7),
        ("Constitution and Polity", 10),
        ("Facts About Kerala", 8),
        ("Daily Current Affairs", 10),
        ("Maths", 10),
        ("English", 10),
        ("Malayalam", 10),
        ("Science", 7),
        ("Excise Special Topics", 20),
    ],
    "beat-forest-officer": [
        ("History", 8),
        ("Geography", 10),
        ("Facts About Kerala", 10),
        ("Constitution and Polity", 8),
        ("Daily Current Affairs", 10),
        ("Science", 8),
        ("Maths", 10),
        ("English", 8),
        ("Malayalam", 8),
        ("Forest and Wildlife Special Topics", 20),
    ],
    "police-constable-band": [
        ("History", 8),
        ("Geography", 7),
        ("Constitution and Polity", 10),
        ("Facts About Kerala", 8),
        ("Daily Current Affairs", 10),
        ("Maths", 10),
        ("English", 10),
        ("Malayalam", 10),
        ("Science", 7),
        ("Band Music and Police Special Topics", 20),
    ],
    "assistant-project-engineer": [
        ("Engineering Maths", 20),
        ("Physics", 10),
        ("Basic Engineering and Drawing", 20),
        ("Constitution and Polity", 10),
        ("Facts About Kerala", 10),
        ("Daily Current Affairs", 10),
        ("English", 10),
        ("Computer", 10),
    ],
}

BLOCKED = ("search engine", "software engineering", "acid properties", "uml stand")


def _topic(name):
    topic = Topic.objects.filter(name__iexact=name).first()
    if topic:
        return topic
    slug = slugify(name)[:150] or "topic"
    topic, _ = Topic.objects.get_or_create(slug=slug, defaults={"name": name})
    if topic.name != name:
        topic.name = name
        topic.save(update_fields=["name"])
    return topic


class Command(BaseCommand):
    help = "Load syllabus MCQs and rebuild October practice sets around those topics"

    def handle(self, *args, **options):
        linked = self._load_questions()
        self.stdout.write(f"Linked syllabus MCQs: {linked}")
        for slug, plan in SET_PLANS.items():
            exam = Exam.objects.filter(slug=slug).first()
            if not exam:
                self.stderr.write(f"Missing exam {slug}")
                continue
            made = self._rebuild_sets(exam, plan)
            self.stdout.write(self.style.SUCCESS(f"{slug}: sets={made}"))

    def _load_questions(self):
        linked = 0
        for item in SYLLABUS_MCQS:
            issues = servability_issues(item["text"], item["options"], item["correct_answer"])
            if issues:
                self.stderr.write(f"Skipped unusable item ({issues}): {item['text'][:80]}")
                continue
            topic = _topic(item["topic"])
            question = Question.objects.filter(text=item["text"]).first()
            if question is None:
                question = Question(
                    topic=topic,
                    sub_topic=item["topic"],
                    text=item["text"],
                    options=item["options"],
                    correct_answer=item["correct_answer"],
                    explanation=item["explanation"],
                    difficulty="medium",
                    language="en",
                    source="manual",
                    status="approved",
                    is_public=True,
                    is_verified=True,
                    verified=True,
                    tags=["syllabus-2026", item["topic"]],
                )
                question.save()
                if not question.is_public:
                    self.stderr.write(f"Hidden by checker: {item['text'][:80]}")
                    continue
            else:
                question.topic = topic
                question.sub_topic = item["topic"]
                question.options = item["options"]
                question.correct_answer = item["correct_answer"]
                question.explanation = item["explanation"]
                question.status = "approved"
                question.is_public = True
                tags = list(question.tags or [])
                if "syllabus-2026" not in tags:
                    tags.append("syllabus-2026")
                question.tags = tags
                question.save()
                if not question.is_public:
                    self.stderr.write(f"Hidden on update: {item['text'][:80]}")
                    continue
            for slug, topics in EXAM_TOPICS.items():
                if item["topic"] not in topics:
                    continue
                exam = Exam.objects.filter(slug=slug).first()
                if exam:
                    exam.questions.add(question)
                    linked += 1
        return linked

    def _pool(self, exam, topic_name):
        tagged = list(
            Question.objects.filter(
                exams=exam,
                is_public=True,
                status="approved",
                tags__contains=["syllabus-2026"],
                sub_topic=topic_name,
            ).order_by("id")
        )
        needle = topic_name.split("—")[0].split(",")[0].strip()
        bank = (
            Question.objects.filter(exams=exam, is_public=True, status="approved")
            .filter(Q(topic__name__icontains=needle) | Q(sub_topic__iexact=topic_name))
            .exclude(id__in=[q.id for q in tagged])
            .order_by("-times_answered", "id")[:120]
        )
        pool = []
        seen = set()
        for question in list(tagged) + list(bank):
            if question.id in seen:
                continue
            hay = f"{question.text} {getattr(question.topic, 'name', '')}".lower()
            if any(phrase in hay for phrase in BLOCKED):
                continue
            if not is_servable(question.text, question.options, question.correct_answer):
                continue
            seen.add(question.id)
            pool.append(question)
        return pool

    def _rebuild_sets(self, exam, plan):
        pools = {topic: self._pool(exam, topic) for topic, _count in plan}
        backup = (
            Question.objects.filter(
                exams=exam,
                is_public=True,
                status="approved",
                topic__name__in=["Facts About Kerala", "Maths", "English", "Malayalam", "History", "Geography"],
            )
            .order_by("-times_answered", "id")[:400]
        )
        backup = [q for q in backup if is_servable(q.text, q.options, q.correct_answer)]
        wider = []
        for question in (
            Question.objects.filter(exams=exam, is_public=True, status="approved")
            .order_by("-times_answered", "id")[:1500]
        ):
            hay = f"{question.text} {getattr(question.topic, 'name', '')}".lower()
            if any(phrase in hay for phrase in BLOCKED):
                continue
            if not is_servable(question.text, question.options, question.correct_answer):
                continue
            wider.append(question)
        papers = []
        for index in range(10):
            used = set()
            chosen = []
            for topic, count in plan:
                pool = pools.get(topic) or []
                if pool:
                    start = (index * 3) % len(pool)
                    rotated = pool[start:] + pool[:start]
                else:
                    rotated = []
                got = 0
                for question in rotated:
                    if got >= count:
                        break
                    if question.id in used:
                        continue
                    chosen.append(question)
                    used.add(question.id)
                    got += 1
            if len(chosen) < 100:
                start = (index * 7) % max(1, len(backup))
                rotated_backup = backup[start:] + backup[:start] if backup else []
                for question in rotated_backup:
                    if len(chosen) >= 100:
                        break
                    if question.id in used:
                        continue
                    chosen.append(question)
                    used.add(question.id)
            if len(chosen) < 100 and wider:
                start = (index * 11) % len(wider)
                rotated_wider = wider[start:] + wider[:start]
                for question in rotated_wider:
                    if len(chosen) >= 100:
                        break
                    if question.id in used:
                        continue
                    chosen.append(question)
                    used.add(question.id)
            if len(chosen) < 100:
                self.stderr.write(f"{exam.slug} set {index + 1} only {len(chosen)} questions")
                return 0
            papers.append(chosen[:100])
        ModelExam.objects.filter(exam=exam, name__startswith="Set ").delete()
        for index, chosen in enumerate(papers):
            paper = ModelExam.objects.create(
                name=f"Set {index + 1} — {exam.name}",
                exam=exam,
                duration_minutes=exam.duration_minutes or 75,
            )
            paper.questions.set(chosen)
            if index == 0:
                special = sum(1 for q in chosen if "syllabus-2026" in (q.tags or []))
                self.stdout.write(f"  set 1 syllabus items {special}/100")
        return len(papers)
