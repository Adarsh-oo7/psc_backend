import os
import sys
import django

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kpsc_backend.settings")
django.setup()

from questionbank.models import Exam, Topic, ExamSyllabus, Question
from django.db.models import Count

TOPIC_TO_EXAMS = {
    223:[2,3,5,6,8,12,13,14,15,16,17], 538:[2,3,5,15,16,17,22,23,24,25], 536:[2,3,5,8,13,14,15,16,17],
    544:[2,3,5,13,14,15,16,17,38], 38:[2,3,5,13,14,15,16,17,38], 10:[2,3,5,13,14,15,16,17,38],
    541:[8,13,14,15,16,17,33], 9:[2,3,5,13,14,15,16,17,38], 537:[5,13,14,15,16,17,18,38],
    539:[2,3,5,13,14,15,16,17,38], 433:[2,3,5,13,14,15,16,17,38], 542:[2,8,13,14,15,16,17],
    547:[15,16,17,38], 540:[2,5,8,13,14,15,16,17,38], 545:[15,16,17,38], 428:[5,16,17,18,38],
    404:[11,30], 34:[2,3,5,13,14,15,16,17,38], 402:[16,17,38], 32:[2,3,5,13,14,15,16,17],
    543:[2,5,15,16,17,38], 535:[15,16,17,38], 53:[2,3,5,15,16,17], 224:[2,3,5,15,22,23,24,25],
    308:[2,5,15,16,17], 339:[22,23,24,49], 42:[2,5,15,16,17], 343:[22,23,49], 414:[33,15,16],
    69:[33,15,16], 411:[33,15,16], 407:[33,15,16], 309:[2,5,15,16,17], 427:[33,16,17,38],
    426:[15,16,17,38], 315:[2,5,15,16,17], 425:[33,16,17,38], 424:[33,16,17,38], 423:[33,16,17,38],
    422:[33,16,17,38], 421:[33,16,17,38], 420:[33,16,17,38], 419:[33,15,16], 418:[33,15,16],
    417:[15,16,38], 416:[33,15,16], 415:[33,16,17,38], 546:[2,5,15,16,17,38], 56:[33,15,16],
    67:[33,15,16], 78:[33,15,16], 313:[2,5,15,16,17], 318:[16,17,21,46,47,48], 320:[16,17,21,46,47,48],
    412:[15,16,17,38], 23:[2,5,15,16,17], 321:[16,17,21,46,47,48], 267:[15,16,17,38],
    322:[16,17,21,46,47,48], 304:[2,5,15,16,17], 306:[2,5,15,16,17], 45:[2,5,15,16,17],
    307:[2,5,15,16,17], 312:[16,17,21,46,47,48], 46:[2,5,15,16,17], 314:[16,17,21,46,47,48],
    316:[2,5,15,16,17], 303:[2,5,15,16,17], 406:[33,15,16], 409:[33,15,16], 329:[16,17,21,46,47,48],
    325:[16,17,21,46,47,48], 324:[16,17,21,46,47,48], 323:[16,17,21,46,47,48], 317:[16,17,21,46,47,48],
    310:[2,5,15,16,17], 305:[2,5,15,16,17], 257:[33,15,16], 124:[22,23,24,25,49], 25:[5,16,17,18,38],
    344:[22,23,49], 410:[33,15,16], 408:[33,15,16], 311:[2,5,15,16,17], 58:[33,15,16],
    331:[2,5,15,16,17], 405:[33,15,16], 357:[46,47,48,21], 332:[2,5,15,16,17], 345:[22,23,49],
    327:[2,5,15,16,17], 326:[2,5,15,16,17], 333:[22,23,49], 346:[22,23,49], 44:[16,17,21,46,47,48],
    328:[2,5,15,16,17], 413:[15,16,17,38], 319:[16,17,21,46,47,48], 87:[2,3,5,15,16,17],
    330:[16,17,21,46,47,48], 549:[15,16,17,38], 548:[15,16,17,38]
}

print("="*60)
print("Seeding ExamSyllabus topic weights for all exams...")
print("="*60)

total_created = 0
total_skipped = 0

# Cache all target exams to reduce DB hits
exam_cache = {}
for eids in TOPIC_TO_EXAMS.values():
    for eid in eids:
        if eid not in exam_cache:
            try:
                exam_cache[eid] = Exam.objects.get(id=eid)
            except Exam.DoesNotExist:
                pass

print(f"Loaded {len(exam_cache)} valid target exams from DB.")

for topic_id, exam_ids in TOPIC_TO_EXAMS.items():
    try:
        topic = Topic.objects.get(id=topic_id)
    except Topic.DoesNotExist:
        print(f"  SKIP: Topic ID {topic_id} not found in DB")
        continue

    # Get question count in General PSC or globally for this topic to estimate weight
    q_count = Question.objects.filter(topic=topic).count()
    # Calculate weight: default to min 1, max 10 based on question density
    estimated_weight = min(10, max(1, q_count // 100 + 1))

    for exam_id in exam_ids:
        if exam_id not in exam_cache:
            total_skipped += 1
            continue

        exam = exam_cache[exam_id]
        # Create relation if it doesn't exist
        _, created = ExamSyllabus.objects.get_or_create(
            exam=exam,
            topic=topic,
            defaults={'num_questions': estimated_weight}
        )
        if created:
            total_created += 1

print("="*60)
print(f"Seeding completed successfully!")
print(f"  Total new relations created: {total_created}")
print(f"  Total skipped (missing exams): {total_skipped}")
print("="*60)
