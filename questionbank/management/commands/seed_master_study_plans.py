from django.core.management.base import BaseCommand
from questionbank.models import Exam, MasterStudyPlan

class Command(BaseCommand):
    help = "Seed official Kerala PSC exam dates, category numbers, official syllabus, and Master Study Plans"

    def handle(self, *args, **options):
        # Default Official Question Pattern for Kerala PSC Objective Exams
        default_question_pattern = {
            "total_questions": 100,
            "total_marks": 100,
            "duration_minutes": 75,
            "mode": "OMR Objective Type",
            "medium": ["Malayalam", "English"],
            "marking_scheme": "+1.0 for correct answer, -0.33 for wrong answer",
        }

        # Default Official Syllabus Structure
        default_official_syllabus = {
            "total_marks": 100,
            "subjects": [
                {
                    "title": "General Knowledge & Kerala Renaissance",
                    "marks": 50,
                    "color": "#10B981",
                    "topics": [
                        "Kerala History, Freedom Struggle & Renaissance Movements",
                        "Indian Geography, Rivers, Soil & Natural Resources",
                        "Indian Constitution, Preamble & Fundamental Rights",
                        "Human Rights Commission & Right to Information (RTI)",
                        "Kerala State Governance, Revenue System & Panchayati Raj",
                        "SCERT Basic Science (Physics, Chemistry & Biology)",
                        "Current Affairs, National & International Events"
                    ]
                },
                {
                    "title": "Simple Arithmetic & Mental Ability",
                    "marks": 20,
                    "color": "#3B82F6",
                    "topics": [
                        "Numbers & Basic Arithmetical Operations",
                        "Fractions, Decimals & Percentages",
                        "Profit, Loss & Simple/Compound Interest",
                        "Time & Work, Time & Distance",
                        "Ratio & Proportion, Average",
                        "Number Series & Coding-Decoding",
                        "Direction Sense & Venn Diagrams"
                    ]
                },
                {
                    "title": "General English",
                    "marks": 20,
                    "color": "#8B5CF6",
                    "topics": [
                        "Types of Sentences & Correct Word Order",
                        "Tenses, Subject-Verb Agreement",
                        "Prepositions & Conjunctions",
                        "Active & Passive Voice, Direct & Indirect Speech",
                        "Vocabulary, Synonyms & Antonyms",
                        "Idioms, Phrases & One Word Substitutes"
                    ]
                },
                {
                    "title": "Regional Language (Malayalam)",
                    "marks": 10,
                    "color": "#F59E0B",
                    "topics": [
                        "പദശുദ്ധി (Correct Usage & Spelling)",
                        "വാക്യശുദ്ധി (Sentence Correction)",
                        "പരിഭാഷ (English to Malayalam Translation)",
                        "ഒറ്റപ്പദം (One Word Substitution)",
                        "ശൈലികൾ, പഴഞ്ചൊല്ലുകൾ (Idioms & Proverbs)",
                        "സമാസവും സന്ധിയും (Malayalam Grammar & Compounds)"
                    ]
                }
            ]
        }

        # Official KPSC Exam Category Numbers & Scheduled Dates
        upcoming_exams = [
            {
                "name": "Company Board LGS",
                "keywords": ["Company Board LGS", "Category 423"],
                "category_number": "Cat. No. 423/2023 & 423/2025",
                "expected_exam_date": "2026-07-18",
                "year": 2026,
            },
            {
                "name": "Last Grade Servant (LGS)",
                "keywords": ["Last Grade Servant", "LGS"],
                "category_number": "Cat. No. 701/2024",
                "expected_exam_date": "2026-08-01",
                "year": 2026,
            },
            {
                "name": "Lower Division Clerk (LDC)",
                "keywords": ["Lower Division Clerk", "LDC"],
                "category_number": "Cat. No. 501/2023 & 502/2023",
                "expected_exam_date": "2026-08-15",
                "year": 2026,
            },
            {
                "name": "Village Field Assistant (VFA)",
                "keywords": ["Village Field Assistant", "VFA"],
                "category_number": "Cat. No. 571/2023",
                "expected_exam_date": "2026-09-19",
                "year": 2026,
            },
            {
                "name": "KSEB Electricity Worker",
                "keywords": ["KSEB Electricity Worker", "KSEB"],
                "category_number": "Cat. No. 612/2023",
                "expected_exam_date": "2026-09-05",
                "year": 2026,
            },
            {
                "name": "Fire & Rescue Officer",
                "keywords": ["Fire & Rescue", "Fireman"],
                "category_number": "Cat. No. 330/2024",
                "expected_exam_date": "2026-09-26",
                "year": 2026,
            },
            {
                "name": "KSRTC Conductor",
                "keywords": ["KSRTC Conductor", "Conductor"],
                "category_number": "Cat. No. 410/2024",
                "expected_exam_date": "2026-10-03",
                "year": 2026,
            },
            {
                "name": "Degree Level Common Preliminary & Mains",
                "keywords": ["Degree Level", "Degree Level Mains"],
                "category_number": "Cat. No. 112/2024",
                "expected_exam_date": "2026-10-10",
                "year": 2026,
            },
            {
                "name": "University LGS",
                "keywords": ["University LGS"],
                "category_number": "Cat. No. 215/2024",
                "expected_exam_date": "2026-10-24",
                "year": 2026,
            },
            {
                "name": "Secretariat Assistant",
                "keywords": ["Secretariat Assistant"],
                "category_number": "Cat. No. 089/2024",
                "expected_exam_date": "2026-11-07",
                "year": 2026,
            },
            {
                "name": "Sub Inspector of Police (SI)",
                "keywords": ["Sub Inspector", "SI Police"],
                "category_number": "Cat. No. 045/2024",
                "expected_exam_date": "2026-11-21",
                "year": 2026,
            },
            {
                "name": "Civil Excise Officer (CEO)",
                "keywords": ["Civil Excise Officer", "Excise Officer"],
                "category_number": "Cat. No. 198/2024",
                "expected_exam_date": "2026-12-05",
                "year": 2026,
            },
        ]

        for item in upcoming_exams:
            exams = Exam.objects.none()
            for kw in item["keywords"]:
                exams = exams | Exam.objects.filter(name__icontains=kw)
            
            if not exams.exists():
                exam = Exam.objects.create(
                    name=item["name"],
                    year=item["year"],
                    category_number=item["category_number"],
                    expected_exam_date=item["expected_exam_date"],
                    official_syllabus=default_official_syllabus,
                    question_pattern=default_question_pattern
                )
                self.stdout.write(self.style.SUCCESS(f"Created Exam: {exam.name}"))
            else:
                for exam in exams.distinct():
                    exam.category_number = item["category_number"]
                    exam.expected_exam_date = item["expected_exam_date"]
                    exam.official_syllabus = default_official_syllabus
                    exam.question_pattern = default_question_pattern
                    exam.save()
                    self.stdout.write(self.style.SUCCESS(f"Updated Exam: {exam.name} ({exam.category_number} - {exam.expected_exam_date})"))

        # Shared Master Study Plans
        plans_data = [
            {
                "exam_keywords": ["Last Grade Servant", "LGS", "Company Board LGS"],
                "title": "Kerala PSC LGS 2026 Master Coaching Roadmap",
                "description": "Comprehensive 60-day study plan covering General Knowledge, Science, Math & Mental Ability, General English, and Malayalam.",
                "estimated_days": 60,
                "syllabus_structure": [
                    {
                        "subject": "General Knowledge & Kerala Renaissance",
                        "weightage": 50,
                        "modules": [
                            {"name": "Kerala History & Renaissance Movement", "target_day": 5},
                            {"name": "Indian Geography & River Systems", "target_day": 10},
                            {"name": "Indian Constitution & Fundamental Rights", "target_day": 15},
                            {"name": "General Science & Environment", "target_day": 22},
                        ]
                    },
                    {
                        "subject": "Simple Arithmetic & Mental Ability",
                        "weightage": 20,
                        "modules": [
                            {"name": "Numbers, Fractions & Decimals", "target_day": 28},
                            {"name": "Percentage, Profit & Loss", "target_day": 34},
                            {"name": "Time & Distance, Simple Interest", "target_day": 40},
                            {"name": "Mental Ability & Series Completion", "target_day": 45},
                        ]
                    },
                    {
                        "subject": "General English",
                        "weightage": 20,
                        "modules": [
                            {"name": "Grammar & Tenses", "target_day": 50},
                            {"name": "Vocabulary, Idioms & Phrases", "target_day": 54},
                        ]
                    },
                    {
                        "subject": "Regional Language (Malayalam)",
                        "weightage": 10,
                        "modules": [
                            {"name": "Malayalam Grammar & Vocabulary", "target_day": 58},
                            {"name": "Important Phrases & Corrections", "target_day": 60},
                        ]
                    }
                ],
                "weekly_milestones": [
                    {"week": 1, "goal": "Master Kerala History, Geography & Renaissance Leaders"},
                    {"week": 2, "goal": "Cover Indian Constitution & General Science Basics"},
                    {"week": 3, "goal": "Complete Arithmetic Core Concepts (Percentage, Profit/Loss)"},
                    {"week": 4, "goal": "Complete Mental Ability & English Grammar Drills"},
                    {"week": 5, "goal": "Solve 5 Full Length LGS Mock Tests & PYQs"},
                    {"week": 6, "goal": "Final Revision & Speed Practice Sessions"},
                ],
                "mock_test_schedule": [15, 30, 45, 52, 58, 60],
                "revision_schedule": [7, 14, 28, 42, 56],
                "pyq_schedule": [10, 20, 30, 40, 50]
            },
            {
                "exam_keywords": ["Village Field Assistant", "VFA"],
                "title": "Village Field Assistant (VFA) 2026 Target Study Roadmap",
                "description": "Structured 45-day intensive study roadmap for VFA (Cat 571/2023). Focuses on SCERT science, arithmetic, and Malayalam.",
                "estimated_days": 45,
                "syllabus_structure": [
                    {
                        "subject": "General Knowledge & Current Affairs",
                        "weightage": 50,
                        "modules": [
                            {"name": "Kerala Governance & Revenue System", "target_day": 5},
                            {"name": "Indian History & Freedom Struggle", "target_day": 12},
                            {"name": "SCERT Basic Science & IT", "target_day": 20},
                        ]
                    },
                    {
                        "subject": "Arithmetic & Mental Ability",
                        "weightage": 20,
                        "modules": [
                            {"name": "Simplification & Ratio Proportion", "target_day": 26},
                            {"name": "Work & Time, Mensuration", "target_day": 32},
                        ]
                    },
                    {
                        "subject": "English & Malayalam",
                        "weightage": 30,
                        "modules": [
                            {"name": "General English Grammar", "target_day": 38},
                            {"name": "Malayalam Vocabulary & Bhashasudhi", "target_day": 45},
                        ]
                    }
                ],
                "weekly_milestones": [
                    {"week": 1, "goal": "Kerala Revenue System & Land Reforms Knowledge"},
                    {"week": 2, "goal": "SCERT Science & Indian Constitution"},
                    {"week": 3, "goal": "Arithmetic Practice & English Grammar"},
                    {"week": 4, "goal": "Full Length VFA Mock Tests & PYQs"},
                ],
                "mock_test_schedule": [10, 20, 30, 40, 45],
                "revision_schedule": [7, 14, 28, 42],
                "pyq_schedule": [8, 18, 28, 38]
            }
        ]

        for data in plans_data:
            exams = Exam.objects.none()
            for kw in data["exam_keywords"]:
                exams = exams | Exam.objects.filter(name__icontains=kw)
            
            for exam in exams.distinct():
                plan, created = MasterStudyPlan.objects.update_or_create(
                    exam=exam,
                    defaults={
                        "title": data["title"],
                        "description": data["description"],
                        "estimated_days": data["estimated_days"],
                        "syllabus_structure": data["syllabus_structure"],
                        "weekly_milestones": data["weekly_milestones"],
                        "mock_test_schedule": data["mock_test_schedule"],
                        "revision_schedule": data["revision_schedule"],
                        "pyq_schedule": data["pyq_schedule"],
                    }
                )
                self.stdout.write(self.style.SUCCESS(f"Saved Master Study Plan for {exam.name}"))

        self.stdout.write(self.style.SUCCESS("Finished seeding official master study plans & exam dates."))
