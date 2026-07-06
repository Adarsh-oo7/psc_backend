# questionbank/syllabus_db.py

SYLLABUS_DATABASE = {
    "village-field-assistant": {
        "name": "Village Field Assistant (VFA)",
        "duration_minutes": 90,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 15},
            {"topic": "Constitution and Polity", "marks": 10},
            {"topic": "Facts About Kerala", "marks": 30},
            {"topic": "Science", "marks": 12},
            {"topic": "Computer", "marks": 3},
            {"topic": "Maths", "marks": 10},
            {"topic": "English", "marks": 10},
            {"topic": "Malayalam", "marks": 10}
        ]
    },
    "company-board-lgs": {
        "name": "Company Board LGS",
        "duration_minutes": 75,
        "negative_marking": 0.0,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 25},
            {"topic": "Facts About Kerala", "marks": 15},
            {"topic": "Daily Current Affairs", "marks": 20},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 10},
            {"topic": "Malayalam", "marks": 10}
        ]
    },
    "ldc-lgs-august-2026": {
        "name": "LDC / BEVCO LDC / Storeman",
        "duration_minutes": 75,
        "negative_marking": 0.0,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 20},
            {"topic": "Daily Current Affairs", "marks": 20},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 10},
            {"topic": "Malayalam", "marks": 10},
            {"topic": "Science", "marks": 20}
        ]
    },
    "kseb-electricity-worker": {
        "name": "KSEB Electricity Worker (Mazdoor)",
        "duration_minutes": 90,
        "negative_marking": -0.33,
        "medium": "English",
        "syllabus": [
            {"topic": "Physics — Electricity & Magnetism", "marks": 60},
            {"topic": "Science", "marks": 40}
        ]
    },
    "fire-and-rescue": {
        "name": "Fire & Rescue Officer Trainee",
        "duration_minutes": 75,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 15},
            {"topic": "Facts About Kerala", "marks": 27},
            {"topic": "Constitution and Polity", "marks": 8},
            {"topic": "Science", "marks": 10},
            {"topic": "Daily Current Affairs", "marks": 10},
            {"topic": "Maths", "marks": 10},
            {"topic": "English", "marks": 10},
            {"topic": "Malayalam", "marks": 10}
        ]
    },
    "ksrtc-conductor": {
        "name": "KSRTC Conductor",
        "duration_minutes": 75,
        "negative_marking": 0.0,
        "medium": "Malayalam",
        "syllabus": [
            {"topic": "Facts About India", "marks": 40},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 20},
            {"topic": "Facts About Kerala", "marks": 20}
        ]
    },
    "university-assistant": {
        "name": "University Assistant",
        "duration_minutes": 75,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 20},
            {"topic": "Constitution and Polity", "marks": 5},
            {"topic": "Facts About Kerala", "marks": 10},
            {"topic": "Science", "marks": 5},
            {"topic": "Computer", "marks": 5},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 20},
            {"topic": "Malayalam", "marks": 15}
        ]
    },
    "secretariat-assistant-auditor": {
        "name": "Secretariat Assistant / Auditor",
        "duration_minutes": 75,
        "negative_marking": -0.33,
        "medium": "English",
        "syllabus": [
            {"topic": "Facts About India", "marks": 20},
            {"topic": "Constitution and Polity", "marks": 5},
            {"topic": "Facts About Kerala", "marks": 10},
            {"topic": "Science", "marks": 5},
            {"topic": "Computer", "marks": 5},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 20},
            {"topic": "Malayalam", "marks": 15}
        ]
    },
    "degree-level-preliminary-exam-2025": {
        "name": "Degree Level Common Prelims",
        "duration_minutes": 75,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 20},
            {"topic": "Constitution and Polity", "marks": 5},
            {"topic": "Facts About Kerala", "marks": 10},
            {"topic": "Science", "marks": 5},
            {"topic": "Computer", "marks": 5},
            {"topic": "Maths", "marks": 20},
            {"topic": "English", "marks": 20},
            {"topic": "Malayalam", "marks": 15}
        ]
    },
    "lp-up-school-teacher": {
        "name": "LP/UP School Teacher (LPST/UPST)",
        "duration_minutes": 75,
        "negative_marking": -0.33,
        "medium": "Malayalam",
        "syllabus": [
            {"topic": "Facts About India", "marks": 50},
            {"topic": "Science", "marks": 30},
            {"topic": "English", "marks": 10},
            {"topic": "Maths", "marks": 10}
        ]
    },
    "kwa-operator": {
        "name": "KWA Operator",
        "duration_minutes": 90,
        "negative_marking": -0.33,
        "medium": "English",
        "syllabus": [
            {"topic": "Physics — Electricity & Magnetism", "marks": 40},
            {"topic": "Science", "marks": 60}
        ]
    },
    "sub-inspector-mains": {
        "name": "Sub Inspector of Police (SI) — Mains",
        "duration_minutes": 75,
        "negative_marking": -0.33,
        "medium": "Malayalam / Tamil / Kannada",
        "syllabus": [
            {"topic": "Facts About India", "marks": 9},
            {"topic": "Facts About Kerala", "marks": 5},
            {"topic": "Constitution and Polity", "marks": 51},
            {"topic": "Science", "marks": 6},
            {"topic": "Daily Current Affairs", "marks": 5},
            {"topic": "Maths", "marks": 10},
            {"topic": "English", "marks": 10},
            {"topic": "Malayalam", "marks": 10}
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
    if 'teacher' in normalized or 'lpst' in normalized or 'upst' in normalized:
        return 'lp-up-school-teacher'
    if 'kwa' in normalized or 'water' in normalized:
        return 'kwa-operator'
    if 'inspector' in normalized or ' si' in normalized:
        return 'sub-inspector-mains'
    if 'ldc' in normalized or 'clerk' in normalized:
        return 'ldc-lgs-august-2026'
        
    return None
