import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kpsc_backend.settings')
django.setup()

from questionbank.models import Exam, Question

mappings = {
    53: 15,  # LDC (Lower Division Clerk) 2024 -> LD Clerk (LDC) 2025
    54: 2,   # Last Grade Servant 2024 -> Last Grade Servant (LGS) 2025
    55: 51,  # Village Field Assistant 2024 -> General PSC (2025)
    56: 34,  # Secretariat Assistant 2024 -> Secretariat Assistant 1000
    57: 3,   # Police Constable (Armed / Civil) 2024 -> Police Constable 2025
    58: 18,  # Sub Inspector of Police 2024 -> Sub Inspector of Police (SI) 2025
    59: 10,  # Civil Excise Officer 2024 -> Civil Excise Officer 2025
    60: 16,  # Degree Level Preliminary Exam 2024 -> Degree Level Preliminary Exam 2025
    61: 27,  # High School Assistant (HSA) 2024 -> High School Assistant (HSA) 2025
    62: 29,  # Higher Secondary School Teacher (HSST) 2024 -> Higher Secondary School Teacher (HSST) 2025
    63: 26,  # LP School Assistant 2024 -> LP / UP School Assistant 2025
    64: 45,  # UP School Assistant 2024 -> UP School Assistant (UPSA) 1000
    65: 16,  # Panchayat Secretary 2024 -> Degree Level Preliminary Exam 2025
    66: 38,  # Kerala Administrative Service (KAS) 2024 -> KAS (Kerala Administrative Service) 1000
    67: 11,  # Forest Guard 2024 -> Beat Forest Officer 2025
    68: 4,   # Fireman 2024 -> Fireman 2025
    69: 20,  # Jail Warden / Warder 2024 -> Assistant Prison Officer 2025
    70: 8,   # LD Typist 2024 -> Typist / Clerk Typist 2025
    71: 46,  # Draftsman / Tracer 2024 -> Assistant Engineer (Civil) 1000
    72: 25,  # Lab Assistant 2024 -> Lab Assistant / Lab Technician 2025
    73: 17,  # Assistant Grade II / III 2024 -> Assistant Grade II 2025
    74: 10,  # Women Civil Excise Officer 2024 -> Civil Excise Officer 2025
    75: 11,  # Beat Forest Officer 2024 -> Beat Forest Officer 2025
    76: 51,  # KSRTC Conductor 2024 -> General PSC (2025)
}

print("Starting 2024 exam seeding/linking...")

for target_id, source_id in mappings.items():
    try:
        target_exam = Exam.objects.get(id=target_id)
        source_exam = Exam.objects.get(id=source_id)
        
        # Check if target exam already has questions
        existing_count = target_exam.questions.count()
        if existing_count == 0:
            source_questions = source_exam.questions.all()
            print(f"Linking {source_questions.count()} questions from '{source_exam}' (ID {source_id}) to '{target_exam}' (ID {target_id})...")
            target_exam.questions.add(*source_questions)
            print(f"Linked successfully! '{target_exam}' now has {target_exam.questions.count()} questions.")
        else:
            print(f"'{target_exam}' already has {existing_count} questions. Skipping.")
    except Exam.DoesNotExist as e:
        print(f"Exam not found: {e}")

print("Seeding/linking completed.")
