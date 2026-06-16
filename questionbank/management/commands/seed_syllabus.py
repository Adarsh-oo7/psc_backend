import os
from django.core.management.base import BaseCommand
from questionbank.models import ExamCategory, Exam, Topic, ExamSyllabus

EXAM_CATEGORIES = [
    "PSC Direct Recruitment",
    "PSC Common Prelims",
    "PSC Education",
    "PSC Gazetted",
    "PSC Technical",
    "PSC KSRTC",
]

EXAMS = [
    # Lower Division Clerk
    {"name": "LDC (Lower Division Clerk)", "slug": "ldc", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Last Grade Servant
    {"name": "Last Grade Servant", "slug": "last-grade-servant", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Village Field Assistant
    {"name": "Village Field Assistant", "slug": "village-field-assistant", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Secretariat Assistant
    {"name": "Secretariat Assistant", "slug": "secretariat-assistant", "category": "PSC Direct Recruitment", "duration_minutes": 90},
    # Police Constable
    {"name": "Police Constable (Armed / Civil)", "slug": "police-constable", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # SI of Police
    {"name": "Sub Inspector of Police", "slug": "si-police", "category": "PSC Direct Recruitment", "duration_minutes": 90},
    # Civil Excise Officer
    {"name": "Civil Excise Officer", "slug": "civil-excise-officer", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Degree Level Prelims
    {"name": "Degree Level Preliminary Exam", "slug": "degree-level-prelims", "category": "PSC Common Prelims", "duration_minutes": 75},
    # HSA / HSST (School Assistant)
    {"name": "High School Assistant (HSA)", "slug": "hsa", "category": "PSC Education", "duration_minutes": 90},
    {"name": "Higher Secondary School Teacher (HSST)", "slug": "hsst", "category": "PSC Education", "duration_minutes": 90},
    # LP/UP School Assistant
    {"name": "LP School Assistant", "slug": "lp-school-assistant", "category": "PSC Education", "duration_minutes": 75},
    {"name": "UP School Assistant", "slug": "up-school-assistant", "category": "PSC Education", "duration_minutes": 75},
    # Panchayat Secretary
    {"name": "Panchayat Secretary", "slug": "panchayat-secretary", "category": "PSC Direct Recruitment", "duration_minutes": 90},
    # KAS (Kerala Administrative Service)
    {"name": "Kerala Administrative Service (KAS)", "slug": "kas", "category": "PSC Gazetted", "duration_minutes": 120},
    # Forest Guard
    {"name": "Forest Guard", "slug": "forest-guard", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Fireman
    {"name": "Fireman", "slug": "fireman", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Jail Warden
    {"name": "Jail Warden / Warder", "slug": "jail-warden", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # LD Typist
    {"name": "LD Typist", "slug": "ld-typist", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Draftsman
    {"name": "Draftsman / Tracer", "slug": "draftsman", "category": "PSC Technical", "duration_minutes": 75},
    # Lab Assistant
    {"name": "Lab Assistant", "slug": "lab-assistant", "category": "PSC Education", "duration_minutes": 75},
    # Assistant Grade
    {"name": "Assistant Grade II / III", "slug": "assistant-grade", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Women Civil Excise Officer  
    {"name": "Women Civil Excise Officer", "slug": "women-civil-excise", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # Beat Forest Officer
    {"name": "Beat Forest Officer", "slug": "beat-forest-officer", "category": "PSC Direct Recruitment", "duration_minutes": 75},
    # KSRTC
    {"name": "KSRTC Conductor", "slug": "ksrtc-conductor", "category": "PSC KSRTC", "duration_minutes": 75},
]

TOPICS = [
    # ─── KERALA HISTORY & CULTURE ───────────────────────────────────
    ("Kerala History — Ancient Period", "kerala-history-ancient", 5, 4),
    ("Kerala History — Medieval Period", "kerala-history-medieval", 5, 4),
    ("Kerala History — Modern Period & Independence", "kerala-history-modern", 8, 6),
    ("Kerala Renaissance Movements", "kerala-renaissance", 6, 5),
    ("Social Reform Leaders of Kerala", "social-reform-leaders", 7, 6),
    ("Prominent Personalities of Kerala", "personalities-kerala", 5, 4),
    ("Kerala Arts & Classical Forms", "kerala-arts", 4, 3),
    ("Kerala Literature", "kerala-literature", 4, 3),
    ("Kerala Geography & Districts", "kerala-geography", 5, 5),
    ("Kerala Economy & Industries", "kerala-economy", 4, 3),
    ("Kerala Government & Governance", "kerala-govt", 4, 3),
    ("Kerala Awards & Honours", "kerala-awards", 3, 2),
    ("Kerala Tribal Communities", "kerala-tribes", 3, 2),
    ("Famous Temples, Churches & Mosques of Kerala", "kerala-religious-sites", 3, 2),
    ("Rivers & Water Bodies of Kerala", "kerala-rivers", 4, 3),
    ("Wildlife Sanctuaries & National Parks — Kerala", "kerala-wildlife", 3, 3),
    ("Festivals of Kerala", "kerala-festivals", 3, 2),
    ("Languages of Kerala — Malayalam", "malayalam-language", 4, 3),

    # ─── INDIA — HISTORY ──────────────────────────────────────────────
    ("Ancient India — Indus Valley & Vedic Period", "ancient-india-indus", 3, 2),
    ("Ancient India — Maurya & Gupta Empire", "ancient-india-maurya-gupta", 3, 2),
    ("Medieval India — Delhi Sultanate", "medieval-india-delhi", 3, 2),
    ("Medieval India — Mughal Empire", "medieval-india-mughal", 4, 3),
    ("India Freedom Movement — Phase 1 (1857–1919)", "freedom-movement-1", 5, 4),
    ("India Freedom Movement — Gandhi & Non-Cooperation", "freedom-movement-gandhi", 6, 5),
    ("India Freedom Movement — 1920–1947", "freedom-movement-2", 6, 5),
    ("Indian National Leaders & Revolutionaries", "indian-national-leaders", 5, 4),
    ("Important Dates in Indian History", "indian-history-dates", 4, 3),

    # ─── INDIA — GEOGRAPHY ────────────────────────────────────────────
    ("Physical Geography of India", "india-physical-geography", 4, 3),
    ("Rivers of India", "india-rivers", 4, 3),
    ("Mountain Ranges & Passes of India", "india-mountains", 3, 2),
    ("Climate & Monsoon of India", "india-climate", 3, 2),
    ("Agriculture in India", "india-agriculture", 3, 3),
    ("Minerals & Natural Resources — India", "india-minerals", 3, 2),
    ("National Parks & Biosphere Reserves — India", "india-national-parks", 3, 2),
    ("Indian States — Capitals & Formation", "india-states", 4, 3),

    # ─── INDIAN POLITY & CONSTITUTION ─────────────────────────────────
    ("Constitution of India — Preamble & Fundamental Rights", "constitution-fundamental-rights", 5, 4),
    ("Constitution of India — DPSP & Duties", "constitution-dpsp", 3, 2),
    ("Parliament of India — Lok Sabha & Rajya Sabha", "parliament-india", 5, 4),
    ("President, PM & Council of Ministers", "president-pm", 4, 3),
    ("Supreme Court & Judiciary", "supreme-court", 4, 3),
    ("State Government — Governor, CM, Legislature", "state-govt", 4, 3),
    ("Local Self Government — Panchayat Raj", "panchayat-raj", 4, 4),
    ("Election Commission & Electoral Process", "election-commission", 3, 2),
    ("Fundamental Duties & Constitutional Amendments", "constitutional-amendments", 3, 2),
    ("Emergency Provisions", "emergency-provisions", 3, 2),
    ("Constitutional Bodies (CAG, UPSC, Finance Commission)", "constitutional-bodies", 3, 2),
    ("RTI Act, Consumer Protection, Legal Rights", "rti-consumer-rights", 3, 2),
    ("Welfare Schemes — Central Government", "central-welfare-schemes", 4, 3),
    ("Welfare Schemes — Kerala Government", "kerala-welfare-schemes", 4, 4),

    # ─── SCIENCE — GENERAL ────────────────────────────────────────────
    ("Biology — Human Body", "biology-human-body", 4, 3),
    ("Biology — Plant Kingdom", "biology-plants", 3, 2),
    ("Biology — Animals & Classification", "biology-animals", 3, 2),
    ("Biology — Diseases & Pathogens", "biology-diseases", 4, 3),
    ("Biology — Nutrition, Vitamins & Deficiencies", "biology-vitamins", 4, 3),
    ("Physics — Motion, Force & Laws", "physics-motion", 3, 2),
    ("Physics — Light, Sound & Optics", "physics-optics", 3, 2),
    ("Physics — Electricity & Magnetism", "physics-electricity", 3, 2),
    ("Chemistry — Elements & Periodic Table", "chemistry-periodic-table", 3, 2),
    ("Chemistry — Acids, Bases & Salts", "chemistry-acids-bases", 3, 2),
    ("Chemistry — Common Chemical Compounds", "chemistry-compounds", 3, 2),
    ("Environmental Science & Ecology", "environmental-science", 4, 3),
    ("Inventions & Discoveries", "inventions-discoveries", 3, 3),
    ("Human Diseases — Communicable & Non-Communicable", "human-diseases", 4, 3),

    # ─── TECHNOLOGY & COMPUTER KNOWLEDGE ──────────────────────────────
    ("Computer Fundamentals & Hardware", "computer-fundamentals", 4, 3),
    ("Internet, Email & Web Basics", "internet-web-basics", 3, 2),
    ("MS Office & Common Software", "ms-office", 3, 2),
    ("Cybersecurity & IT Act", "cybersecurity-it-act", 3, 2),
    ("Space Technology — ISRO & Missions", "space-isro", 3, 2),
    ("Emerging Technologies (AI, IoT, Blockchain basics)", "emerging-tech", 2, 2),

    # ─── ECONOMICS ────────────────────────────────────────────────────
    ("Indian Economy — Basics & GDP", "indian-economy-basics", 4, 3),
    ("Indian Economy — Banking & RBI", "indian-economy-rbi", 4, 3),
    ("Indian Economy — Taxation & Budget", "indian-economy-budget", 3, 2),
    ("Five Year Plans & NITI Aayog", "five-year-plans", 3, 2),
    ("International Trade & WTO", "international-trade", 2, 2),
    ("Poverty, Unemployment & Social Indicators", "poverty-unemployment", 3, 2),

    # ─── CURRENT AFFAIRS ──────────────────────────────────────────────
    ("Current Affairs — Kerala (Monthly)", "current-affairs-kerala", 10, 8),
    ("Current Affairs — India (Monthly)", "current-affairs-india", 8, 6),
    ("Current Affairs — International (Monthly)", "current-affairs-international", 5, 4),
    ("Awards — National & International", "awards-national-international", 3, 3),
    ("Sports & Games — National", "sports-national", 3, 2),
    ("Sports & Games — International", "sports-international", 3, 2),
    ("Books & Authors", "books-authors", 2, 2),
    ("Persons in News", "persons-in-news", 3, 3),
    ("Important Days & Observances", "important-days", 3, 2),

    # ─── MATHEMATICS (for LDC/Secretariat/Degree level) ──────────────
    ("Number System & HCF/LCM", "number-system", 4, 3),
    ("Simplification & BODMAS", "simplification-bodmas", 4, 3),
    ("Fractions, Decimals & Percentages", "fractions-decimals", 4, 3),
    ("Ratio, Proportion & Variation", "ratio-proportion", 3, 2),
    ("Time & Work", "time-work", 3, 2),
    ("Time, Speed & Distance", "time-speed-distance", 3, 2),
    ("Profit, Loss & Discount", "profit-loss", 3, 2),
    ("Simple & Compound Interest", "simple-compound-interest", 3, 2),
    ("Averages & Mixtures", "averages-mixtures", 3, 2),
    ("Algebra — Equations & Identities", "algebra", 3, 2),
    ("Geometry — Lines, Angles, Triangles", "geometry-lines-triangles", 3, 2),
    ("Mensuration — Areas & Volumes", "mensuration", 3, 2),
    ("Data Interpretation — Tables & Graphs", "data-interpretation", 3, 2),
    ("Logical Reasoning & Series", "logical-reasoning", 5, 4),
    ("Mental Ability & Analogy", "mental-ability-analogy", 5, 4),

    # ─── ENGLISH (for LDC/Secretariat/Degree level) ───────────────────
    ("English Grammar — Parts of Speech", "english-grammar-pos", 3, 2),
    ("English Grammar — Tenses", "english-grammar-tenses", 3, 2),
    ("English — Active & Passive Voice", "english-active-passive", 2, 2),
    ("English — Direct & Indirect Speech", "english-direct-indirect", 2, 2),
    ("English — Synonyms & Antonyms", "english-synonyms-antonyms", 4, 3),
    ("English — One Word Substitution", "english-one-word", 3, 2),
    ("English — Idioms & Phrases", "english-idioms-phrases", 3, 2),
    ("English — Reading Comprehension", "english-comprehension", 3, 2),
    ("English — Spelling & Vocabulary", "english-spelling", 2, 2),

    # ─── WORLD GEOGRAPHY ──────────────────────────────────────────────
    ("World Map & Continents", "world-geography-continents", 3, 2),
    ("Important Countries — Capitals & Currencies", "world-countries-capitals", 3, 2),
    ("World Rivers & Mountains", "world-rivers-mountains", 2, 2),
    ("Climate Zones & Natural Phenomena", "world-climate", 2, 2),
    ("International Organizations (UN, NATO, ASEAN)", "international-organizations", 3, 2),

    # ─── WORLD HISTORY ────────────────────────────────────────────────
    ("World History — Revolutions (French, American, Russian)", "world-revolutions", 3, 2),
    ("World Wars I & II", "world-wars", 3, 2),
    ("Cold War & Post-Cold War", "cold-war", 2, 2),
    ("Famous World Leaders", "world-leaders", 2, 2),
]

class Command(BaseCommand):
    help = "Seeds all Kerala PSC exam categories, exams, and topics"

    def handle(self, *args, **kwargs):
        # 1. Create categories
        for i, cat_name in enumerate(EXAM_CATEGORIES):
            cat, created = ExamCategory.objects.get_or_create(
                name=cat_name, defaults={'order': i}
            )
            if created:
                self.stdout.write(f"Created category: {cat_name}")

        # 2. Create exams
        for exam in EXAMS:
            cat_obj = ExamCategory.objects.get(name=exam['category'])
            exam_obj, created = Exam.objects.get_or_create(
                slug=exam['slug'],
                defaults={
                    'name': exam['name'],
                    'category': cat_obj,
                    'duration_minutes': exam['duration_minutes'],
                    'year': 2024
                }
            )
            if created:
                self.stdout.write(f"Created exam: {exam['name']}")

        # 3. Create topics
        for topic_name, slug, _, _ in TOPICS:
            topic, created = Topic.objects.get_or_create(
                slug=slug,
                defaults={'name': topic_name, 'institute': None}
            )
            if created:
                self.stdout.write(f"Created topic: {topic_name}")

        # 4. Create ExamSyllabus entries
        try:
            ldc = Exam.objects.get(slug='ldc')
            last_grade = Exam.objects.get(slug='last-grade-servant')
            for topic_name, slug, ldc_count, lg_count in TOPICS:
                topic = Topic.objects.get(slug=slug)
                
                # Create for LDC
                ldc_syllabus, created = ExamSyllabus.objects.get_or_create(
                    exam=ldc, topic=topic,
                    defaults={'num_questions': ldc_count}
                )
                if not created and ldc_syllabus.num_questions != ldc_count:
                    ldc_syllabus.num_questions = ldc_count
                    ldc_syllabus.save()

                # Create for Last Grade
                lg_syllabus, created = ExamSyllabus.objects.get_or_create(
                    exam=last_grade, topic=topic,
                    defaults={'num_questions': lg_count}
                )
                if not created and lg_syllabus.num_questions != lg_count:
                    lg_syllabus.num_questions = lg_count
                    lg_syllabus.save()
                    
            self.stdout.write(self.style.SUCCESS("Syllabus distribution created/updated successfully."))
        except Exam.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"Required exam not found for syllabus linking: {e}"))

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))
