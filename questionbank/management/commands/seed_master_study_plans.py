from django.core.management.base import BaseCommand
from questionbank.models import Exam, MasterStudyPlan, Topic

class Command(BaseCommand):
    help = "Seed shared Master Study Plans for top exams (LGS 2026, VFA, LDC, Company Board LGS, etc.)"

    def handle(self, *args, **options):
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
                "description": "Structured 45-day intensive study roadmap for VFA (Cat 571/2025). Focuses on SCERT science, arithmetic, and Malayalam.",
                "estimated_days": 45,
                "syllabus_structure": [
                    {
                        "subject": "General Knowledge & SCERT Science",
                        "weightage": 50,
                        "modules": [
                            {"name": "Kerala Facts, Districts & Wildlife", "target_day": 7},
                            {"name": "SCERT Basic Science (Physics & Chemistry)", "target_day": 14},
                            {"name": "Indian National Movement", "target_day": 20},
                        ]
                    },
                    {
                        "subject": "Arithmetic & Reasoning",
                        "weightage": 30,
                        "modules": [
                            {"name": "Basic Mathematics & Simplification", "target_day": 27},
                            {"name": "Ratio, Proportions & Averages", "target_day": 33},
                        ]
                    },
                    {
                        "subject": "Malayalam & English",
                        "weightage": 20,
                        "modules": [
                            {"name": "Malayalam Usage & Corrections", "target_day": 40},
                            {"name": "General English Vocabulary", "target_day": 45},
                        ]
                    }
                ],
                "weekly_milestones": [
                    {"week": 1, "goal": "Complete SCERT Science & Kerala Geography"},
                    {"week": 2, "goal": "Finish Freedom Struggle & Arithmetic Basics"},
                    {"week": 3, "goal": "Complete Reasoning & Malayalam Section"},
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

        self.stdout.write(self.style.SUCCESS("Finished seeding master study plans."))
