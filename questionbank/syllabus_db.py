# questionbank/syllabus_db.py
# Verified against official Kerala PSC notifications — July 2026
# Sources: keralapsc.gov.in, entri.app, challengerapp.in, thesupernotes.com

SYLLABUS_DATABASE = {

    # ─────────────────────────────────────────────
    # 1. VILLAGE FIELD ASSISTANT (VFA)
    # Cat: 571/2025 | Exam: Sept 19, 2026 | Neg: -1/3
    # ─────────────────────────────────────────────
    "village-field-assistant": {
        "name": "Village Field Assistant (VFA)",
        "cat_no": "571/2025",
        "exam_date": "2026-09-19",
        "level": "SSLC",
        "duration_minutes": 90,
        "total_marks": 100,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "History", "marks": 5},
            {"topic": "Geography", "marks": 5},
            {"topic": "Economics", "marks": 5},
            {"topic": "Constitution and Polity", "marks": 5},
            {"topic": "Facts About Kerala", "marks": 5},
            {"topic": "Biology and Public Health", "marks": 6},
            {"topic": "Physics", "marks": 3},
            {"topic": "Chemistry", "marks": 3},
            {"topic": "Arts Culture Literature Sports", "marks": 5},
            {"topic": "Computer", "marks": 3},
            {"topic": "Important Laws", "marks": 5},
            {"topic": "Vocational Agriculture Topics", "marks": 20},
            {"topic": "Maths", "marks": 10},
            {"topic": "English", "marks": 10},
            {"topic": "Malayalam", "marks": 10},
        ]
    },

    # ─────────────────────────────────────────────
    # 2. COMPANY BOARD LGS
    # Cat: 423/2025 | Exam: July 18, 2026 | Neg: -1/3
    # ─────────────────────────────────────────────
    "company-board-lgs": {
        "name": "Company Board LGS",
        "cat_no": "423/2025",
        "exam_date": "2026-07-18",
        "level": "SSLC",
        "duration_minutes": 75,
        "total_marks": 100,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 20},
            {"topic": "Facts About Kerala", "marks": 20},
            {"topic": "Daily Current Affairs", "marks": 20},
            {"topic": "Science", "marks": 10},
            {"topic": "Public Health", "marks": 10},
            {"topic": "Maths", "marks": 20},
        ]
    },

    # ─────────────────────────────────────────────
    # 3. LGS — GENERAL GOVERNMENT DEPARTMENTS
    # Standard LGS (non-Company Board) | Neg: None
    # ─────────────────────────────────────────────
    "lgs-general": {
        "name": "Last Grade Servant (General)",
        "cat_no": "Various",
        "exam_date": "2026-08-01",
        "level": "SSLC",
        "duration_minutes": 75,
        "total_marks": 100,
        "negative_marking": 0.0,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 20},
            {"topic": "Facts About Kerala", "marks": 20},
            {"topic": "Daily Current Affairs", "marks": 20},
            {"topic": "Science", "marks": 10},
            {"topic": "Public Health", "marks": 10},
            {"topic": "Maths", "marks": 20},
        ]
    },

    # ─────────────────────────────────────────────
    # 4. LDC / BEVCO LDC / STOREMAN
    # Cat: 619/2025, 620/2025, 618/2025 | Exam: Aug 1, 2026
    # ─────────────────────────────────────────────
    "ldc-lgs-august-2026": {
        "name": "LDC / BEVCO LDC / Storeman",
        "cat_no": "619/2025, 620/2025, 618/2025",
        "exam_date": "2026-08-01",
        "level": "SSLC",
        "duration_minutes": 75,
        "total_marks": 100,
        "negative_marking": 0.0,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 20},
            {"topic": "Daily Current Affairs", "marks": 20},
            {"topic": "Science", "marks": 20},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 10},
            {"topic": "Malayalam", "marks": 10},
        ]
    },

    # ─────────────────────────────────────────────
    # 5. KSEB ELECTRICITY WORKER (MAZDOOR)
    # Cat: 021/2026 | Exam: Sept 30, 2026 | Neg: -1/3 | Medium: English
    # ─────────────────────────────────────────────
    "kseb-electricity-worker": {
        "name": "KSEB Electricity Worker (Mazdoor)",
        "cat_no": "021/2026",
        "exam_date": "2026-09-30",
        "level": "ITI",
        "duration_minutes": 90,
        "total_marks": 100,
        "negative_marking": -0.33,
        "medium": "English",
        "syllabus": [
            {"topic": "Basic Electricity — Fundamentals, Resistance, Conductors, Wires", "marks": 10},
            {"topic": "Ohm's Law — Kirchhoff's Law, Temperature Effects, Cell Types", "marks": 10},
            {"topic": "Magnetism — Properties, Electromagnetism, Fleming's Rules, Faraday's Laws", "marks": 10},
            {"topic": "Alternating Current and Earthing — AC, Earthing, Wiring, Megger", "marks": 10},
            {"topic": "DC Machines — Generators, DC Motors, Starters", "marks": 10},
            {"topic": "AC Motors — Single & 3 Phase, DOL, Star-Delta Starters", "marks": 10},
            {"topic": "Instruments and Transformers — Measuring Instruments, EMF Equation", "marks": 10},
            {"topic": "Illumination and Electronics — Lamps, Semiconductors, Diodes, Transistors", "marks": 10},
            {"topic": "Power Generation — Energy Sources, Types of Power Generation", "marks": 10},
            {"topic": "Transmission and Distribution — AC vs DC Comparison", "marks": 10},
        ]
    },

    # ─────────────────────────────────────────────
    # 6. FIRE & RESCUE OFFICER TRAINEE
    # Cat: 551/2025 | Exam: July 4, 2026 | Neg: -1/3
    # ─────────────────────────────────────────────
    "fire-and-rescue": {
        "name": "Fire & Rescue Officer Trainee",
        "cat_no": "551/2025",
        "exam_date": "2026-07-04",
        "level": "SSLC",
        "duration_minutes": 75,
        "total_marks": 100,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "History", "marks": 5},
            {"topic": "Geography", "marks": 5},
            {"topic": "Economics", "marks": 5},
            {"topic": "Constitution and Polity", "marks": 8},
            {"topic": "Facts About Kerala", "marks": 3},
            {"topic": "Biology and Public Health", "marks": 4},
            {"topic": "Physics", "marks": 3},
            {"topic": "Chemistry", "marks": 3},
            {"topic": "Arts Culture Literature Sports", "marks": 4},
            {"topic": "Daily Current Affairs", "marks": 10},
            {"topic": "Maths", "marks": 10},
            {"topic": "English", "marks": 10},
            {"topic": "Malayalam", "marks": 10},
            {"topic": "Fire and Rescue Special Topics", "marks": 20},
        ]
    },

    # ─────────────────────────────────────────────
    # 7. KSRTC CONDUCTOR (RESERVE)
    # Neg: None | Medium: Malayalam
    # ─────────────────────────────────────────────
    "ksrtc-conductor": {
        "name": "KSRTC Conductor",
        "cat_no": "Various",
        "exam_date": None,
        "level": "SSLC",
        "duration_minutes": 75,
        "total_marks": 100,
        "negative_marking": 0.0,
        "medium": "Malayalam",
        "syllabus": [
            {"topic": "History", "marks": 10},
            {"topic": "Geography", "marks": 10},
            {"topic": "Constitution and Polity", "marks": 5},
            {"topic": "Facts About Kerala", "marks": 5},
            {"topic": "Science", "marks": 5},
            {"topic": "Daily Current Affairs", "marks": 5},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 20},
            {"topic": "KSRTC Conductor Special Topics", "marks": 20},
        ]
    },

    # ─────────────────────────────────────────────
    # 8. UNIVERSITY ASSISTANT
    # Neg: -1/3 | Degree Level
    # ─────────────────────────────────────────────
    "university-assistant": {
        "name": "University Assistant",
        "cat_no": "Various",
        "exam_date": None,
        "level": "Degree",
        "duration_minutes": 75,
        "total_marks": 100,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "History", "marks": 10},
            {"topic": "Geography", "marks": 5},
            {"topic": "Economics", "marks": 5},
            {"topic": "Constitution and Polity", "marks": 10},
            {"topic": "Arts Culture Literature Sports", "marks": 10},
            {"topic": "Computer", "marks": 5},
            {"topic": "Science", "marks": 5},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 20},
            {"topic": "Malayalam", "marks": 10},
        ]
    },

    # ─────────────────────────────────────────────
    # 9. SECRETARIAT ASSISTANT / AUDITOR
    # Prelims = Degree Level Common Prelims | Neg: -1/3
    # ─────────────────────────────────────────────
    "secretariat-assistant-auditor": {
        "name": "Secretariat Assistant / Auditor",
        "cat_no": "576/2024 (completed); new notification expected",
        "exam_date": None,
        "level": "Degree",
        "duration_minutes": 75,
        "total_marks": 100,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "History", "marks": 10},
            {"topic": "Geography", "marks": 5},
            {"topic": "Economics", "marks": 5},
            {"topic": "Constitution and Polity", "marks": 10},
            {"topic": "Arts Culture Literature Sports", "marks": 10},
            {"topic": "Computer", "marks": 5},
            {"topic": "Science", "marks": 5},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 20},
            {"topic": "Malayalam", "marks": 10},
        ]
    },

    # ─────────────────────────────────────────────
    # 10. DEGREE LEVEL COMMON PRELIMINARY EXAM
    # Neg: -1/3 | Covers: SI, Secretariat, Uni Asst, etc.
    # ─────────────────────────────────────────────
    "degree-level-preliminary-exam-2025": {
        "name": "Degree Level Common Prelims",
        "cat_no": "Multiple",
        "exam_date": "2026-05-02",
        "level": "Degree",
        "duration_minutes": 75,
        "total_marks": 100,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "History", "marks": 10},
            {"topic": "Geography", "marks": 5},
            {"topic": "Economics", "marks": 5},
            {"topic": "Constitution and Polity", "marks": 10},
            {"topic": "Arts Culture Literature Sports", "marks": 10},
            {"topic": "Computer", "marks": 5},
            {"topic": "Science", "marks": 5},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 20},
            {"topic": "Malayalam", "marks": 10},
        ]
    }
}

# Helpers to map loose user preferred exam strings to official keys
def resolve_exam_slug(exam_slug):
    if not exam_slug:
        return None
    normalized = exam_slug.replace('_', '-').lower()
    
    # Direct match
    if normalized in SYLLABUS_DATABASE:
        return normalized
        
    # Match synonyms/substrings
    if 'lgs' in normalized:
        return 'company-board-lgs'
    if 'vfa' in normalized or 'village' in normalized:
        return 'village-field-assistant'
    if 'kseb' in normalized:
        return 'kseb-electricity-worker'
    if 'conductor' in normalized:
        return 'ksrtc-conductor'
    if 'fire' in normalized:
        return 'fire-and-rescue'
    if 'university' in normalized:
        return 'university-assistant'
    if 'secretariat' in normalized:
        return 'secretariat-assistant-auditor'
    if 'degree' in normalized:
        return 'degree-level-preliminary-exam-2025'
    if 'ldc' in normalized or 'clerk' in normalized:
        return 'ldc-lgs-august-2026'
        
    return None
