import os
import sys
import django

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kpsc_backend.settings")
django.setup()

from questionbank.models import Exam, Syllabus

# ─── Helper ──────────────────────────────────────────────────────────────────
def add_syllabus(exam_id, parts):
    """
    parts = list of (order, title, description)
    Formats parts into a single markdown block and updates the Syllabus details.
    """
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        print(f"  SKIP: Exam ID {exam_id} not found")
        return
        
    # Format parts into a single details text
    formatted_details = ""
    for order, title, description in parts:
        formatted_details += f"### {title}\n{description}\n\n"
        
    # Update or create the detailed Syllabus record
    syllabus, created = Syllabus.objects.get_or_create(exam=exam)
    syllabus.details = formatted_details.strip()
    syllabus.save()
    
    print(f"  OK: {exam.name} (ID:{exam_id}) — Syllabus details updated.")

print("="*60)
print("Adding official Kerala PSC syllabi to the database")
print("="*60)

# ─── 1. LGS — Last Grade Servant (ID:2) ───────────────────────────────────
lgs_parts = [
    (1, "Part I: General Knowledge (40 Marks)",
     """1. Indian Freedom Struggle – Political, social, and cultural movements related to the freedom struggle era; National movements; Freedom fighters; Administrative systems. (5 Marks)
2. Post-Independence India – Major challenges, wars, Five Year Plans, progress and achievements in various sectors. (5 Marks)
3. Rights and Duties of a Citizen – Fundamental rights and duties; Indian Constitution – basic information. (5 Marks)
4. Geographical features of India – Borders and boundaries; Basic information about India. (5 Marks)
5. Kerala – Geography, basic information, rivers and backwaters, various hydroelectric projects, wildlife sanctuaries and parks, fisheries, sports, local self-government institutions. (10 Marks)
6. Social and political movements in Kerala related to the Indian freedom struggle; Renaissance leaders. (5 Marks)
7. Science & Technology sector; Arts & Cultural sector; Political, Economic, Literary sector; Sports sector – related information. (5 Marks)"""),

    (2, "Part II: Current Affairs (20 Marks)",
     "Recent national and international events, key news stories, and developments in science, technology, arts, culture, politics, economy, literature, and sports."),

    (3, "Part III: Science (10 Marks)",
     """(i) Life Science / Biology (5 Marks):
1. General knowledge about the human body
2. Vitamins and deficiency diseases
3. Major food and agricultural crops of Kerala
4. Forests, forest resources, social forestry
5. Environment and environmental problems

(ii) Physical Science / Chemistry (5 Marks):
1. Atom and its structure
2. Ores and minerals
3. Elements and their classification
4. Hydrogen and Oxygen
5. Chemistry in daily life
6. Matter and mass
7. Work and energy
8. Energy and its transformation
9. Heat and temperature
10. Motions and forces in nature
11. Sound and light
12. Solar system and its features"""),

    (4, "Part IV: Public Health (10 Marks)",
     """1. Communicable diseases and causative organisms
2. Basic health knowledge
3. Lifestyle diseases
4. Health welfare activities in Kerala"""),

    (5, "Part V: Simple Arithmetic, Mental Ability & Observation Skills (20 Marks)",
     """(i) Simple Arithmetic (10 Marks):
I. Numbers and basic operations
II. LCM and HCF
III. Fractions
IV. Decimal numbers
V. Squares and square roots
VI. Average
VII. Profit and loss
VIII. Time and distance

(ii) Mental Ability and Observation Skills (10 Marks):
I. Problems using mathematical symbols
II. Series
III. Analogies
IV. Classification
V. Meaningful arrangement of words
VI. Odd one out
VII. Age-related problems
VIII. Position determination

NOTE: Apart from the above topics, questions from other topics prescribed for the educational qualification of the post may also appear."""),
]
add_syllabus(2, lgs_parts)

# ─── 2. Police Constable (ID:3) ───────────────────────────────────────────
pc_parts = [
    (1, "Part I: General Knowledge (40 Marks)",
     """(1) History (5 Marks):
Kerala – Arrival of Europeans; Contributions of Europeans; History of Travancore from Marthanda Varma to Sree Chithirathirunnal; Social, religious and reform movements; National movement in Kerala; Literary sources of Kerala History; United Kerala Movement; Political and Social History of Kerala after 1956.
India – Political History; British establishment; First War of Independence; Formation of INC; Swadeshi Movement; Social Reform movements; Newspapers; Literature and Art during freedom struggle; Independence Movement & Mahatma Gandhi; Post-independence period; State reorganisation; Development in Science, Education and Technology; Foreign policy.
World – Great Revolution in England; American War of Independence; French Revolution; Russian Revolution; Chinese Revolution; Political History after Second World War; UNO and other International Organisations.

(2) Geography (5 Marks):
Basics of Geography – Earth structure; Atmosphere; Rocks; Landforms; Pressure belt and winds; Temperature and seasons; Global issues; Global warming; Various forms of pollution; Maps; Topographic maps and signs; Remote sensing; Geographic Information System; Oceans and movements; Continents; World nations and their specific features.
India – Physiography; States and their features; Northern mountain region; Rivers; Northern Great Plain; Peninsular Plateau; Coastal Plain; Climate; Natural vegetation; Agriculture; Minerals and industries; Energy sources; Transport system.
Kerala – Physiography; Districts and their features; Rivers; Climate; Natural vegetation; Wildlife; Agriculture and research centres; Minerals and industries; Energy sources; Transport system.

(3) Economics (5 Marks):
India: Economy; Five Year Plans; New Economic Reforms; Planning Commission; NITI Aayog; Financial institutions; Agriculture – major crops; Green Revolution; Minerals.

(4) Indian Constitution (8 Marks):
Constituent Assembly; Preamble; Citizenship; Fundamental Rights; Directive Principles; Fundamental Duties; Structure of Government; Important Constitutional Amendments (42, 44, 52, 73, 74, 86, 91); Panchayati Raj; Constitutional institutions and their functions; Union List; State List; Concurrent List.

(5) Kerala – Governance and Administration (3 Marks):
Kerala State Civil Service; Constitutional institutions; Various Commissions; Socio-economic and commercial basic facts; Grievance redressal authority; Wetland conservation; Employment and labour; National Rural Employment Programmes; Land reforms; Protection of women, children, senior citizens; Social welfare and security.

(6) Life Science and Public Health (4 Marks):
1. General knowledge about the human body
2. Vitamins, minerals and deficiency diseases
3. Communicable diseases and causative organisms
4. Health welfare activities in Kerala
5. Lifestyle diseases
6. Basic health knowledge
7. Environment and environmental problems

(7) Physical Science (3 Marks):
Branches of Physical Science; Matter; Units and measurements; Motion and Newton's laws; Momentum; Projectile motion; ISRO space achievements; Light – lenses and mirrors; Various phenomena of light; Electromagnetic spectrum; Sound – types of waves; Speed of light in different media; Resonance; Periodic motion.

(8) Chemistry (3 Marks):
Atom; Molecule; States of matter; Radioactivity; Gas laws; Aqua Regia; Molecules; Periodic table; Metals and non-metals; Chemical and physical changes; Chemical reactions; Solutions; Mixtures; Compounds; Metals; Alloys; Acids and Alkalis; pH value; Alkaloids.

(9) Arts, Sports, Literature and Culture (4 Marks):
Art: Major visual and performing arts of Kerala – their origin, spread, practice; Famous places, institutions, personalities, artists, writers.
Sports: Major sports personalities of Kerala, India and the world; Their sports, achievements and honours; Major awards; Major trophies; Olympics; Asian Games; Commonwealth Games; SAFF Games; National Games.
Literature: Major literary movements in Malayalam; Early works and authors; Major works and authors in each movement; Pen names; Characters and works; Famous lines; Malayalam journalism; Major awards.
Culture: Major festivals in Kerala; Famous events and venues; Cultural centres and places of worship; Cultural leaders and their contributions."""),

    (2, "Part II: Current Affairs (10 Marks)",
     "Recent national and international events in science, technology, arts, culture, politics, economy, literature, and sports."),

    (3, "Part III: Simple Arithmetic, Mental Ability & Observation Skills (10 Marks)",
     """(1) Simple Arithmetic (5 Marks):
Numbers and basic operations; Fractions and decimal numbers; Percentage; Profit and loss; Simple and compound interest; Ratio and proportion; Time and distance; Time and work; Average; Laws of exponents; Mensuration; Progressions.

(2) Mental Ability and Observation Skills (5 Marks):
Series (number and alphabet); Problems on mathematical signs; Position determination; Analogy; Odd man out; Numerical ability; Coding and decoding; Family relations; Sense of direction; Time and angles; Time and clock reflection; Date and calendar; Clerical ability."""),

    (4, "Part IV: General English (10 Marks)",
     """Grammar (5 Marks): Types of sentences; Parts of speech; Subject-verb agreement; Articles; Auxiliary verbs; Question tags; Infinitive and gerunds; Tenses; Conditional sentences; Prepositions; Correlatives; Direct and indirect speech; Active and passive voice; Correction of sentences; Degrees of comparison.
Vocabulary (5 Marks): Singular & plural; Gender; Collective nouns; Word formation; Compound words; Synonyms; Antonyms; Phrasal verbs; Foreign words and phrases; One word substitutes; Commonly confused words; Spelling; Idioms; Common abbreviations."""),

    (5, "Part V: Regional Language – Malayalam/Kannada/Tamil (10 Marks)",
     """Malayalam: Word purity; Sentence purity; Translation; Single word; Synonyms; Antonyms; Idioms and proverbs; Equivalent word; Join words; Gender; Number; Separate writing; Compound word formation.
Kannada: Word purity; Correct sentence; Translation; One word substitution; Synonyms; Antonyms; Idioms and proverbs; Equivalent word; Join the word; Gender; Number; Sort and write.
Tamil: Correct word; Correct sentence structure; Translation; Single word; Synonyms; Antonyms; Phrases and proverbs; Equal word; Join the word; Gender classification; Singular/plural; Separate; Adding phrases."""),

    (6, "Part VI: Special Topics – Job-Related Subjects (20 Marks)",
     """PART I (4 Marks) – Offences (IPC/BNS):
General Exceptions; Offences Against Body (culpable homicide, murder, causing death by negligence, dowry death, hurt, grievous hurt, wrongful restraint and confinement, kidnapping, abduction, trafficking, rape, sexual offences against women); Offences Against Property (theft, extortion, robbery, dacoity, criminal breach of trust, stolen property, cheating).

PART II (3 Marks) – CrPC/BNSS:
Definitions (bailable/cognizable/non-cognizable offence, investigation, summons case, warrant case); Arrest procedures; Summons and warrants; Seizure; Information to police and investigation powers.

PART III (2 Marks) – Evidence Act/BSA:
Admissibility of statements by accused; Statements of persons who are dead or cannot be found; Opinion of experts.

PART IV (Special Laws):
(1) Kerala Police Act 2011 (3 Marks): Selected sections.
(2) NDPS Act 1985 (2 Marks): Selected sections.
(3) POCSO Act 2012 (2 Marks): Selected sections.
(4) IT Act (2 Marks): Security and related offences.
(5) RTI Act 2005 (2 Marks): Exemptions and power.

NOTE: Apart from the above topics, questions from other topics prescribed for the educational qualification of the post may also appear."""),
]
add_syllabus(3, pc_parts)

# ─── 3. Civil Police Officer CPO (ID:5) ──────────────────────────────────
cpo_parts = [
    (1, "Part I: General Knowledge (40 Marks)",
     "जीके, भूगोल, इतिहास, अर्थशास्त्र, संविधान, कला, खेल और संस्कृति - 12वीं / प्लस टू स्तर के स्तर के."),
    (2, "Part II: Current Affairs (10 Marks)",
     "राष्ट्रीय और अंतर्राष्ट्रीय सामयिक घटनाएँ।"),
    (3, "Part III: Simple Arithmetic, Mental Ability & Observation Skills (10 Marks)",
     "अंकगणित और मानसिक योग्यता।"),
    (4, "Part IV: General English (10 Marks)",
     "अंग्रेजी व्याकरण और शब्दावली।"),
    (5, "Part V: Regional Language – Malayalam/Kannada/Tamil (10 Marks)",
     "क्षेत्रीय भाषा योग्यता।"),
    (6, "Part VI: Special Topics – Job-Related Subjects (20 Marks)",
     "आईपीसी, सीआरपीसी, भारतीय साक्ष्य अधिनियम और केरल पुलिस अधिनियम के अंतर्गत कानून।"),
]
add_syllabus(5, cpo_parts)

# ─── 4. LD Clerk / LDC (ID:15) ────────────────────────────────────────────
ldc_parts = [
    (1, "Part I: General Knowledge (50 Marks)",
     "History (5 Marks), Geography (5 Marks), Economics (5 Marks), Constitution (5 Marks), Kerala Governance (5 Marks), Life Science & Health (6 Marks), Physical Science (3 Marks), Chemistry (3 Marks), Arts/Sports/Literature/Culture (5 Marks), Computer Basics (3 Marks), Important Laws (RTI, Consumer, POCSO, Domestic Violence - 5 Marks)."),
    (2, "Part II: Current Affairs (20 Marks)",
     "Recent national and international events in science, technology, arts, culture, politics, economy, literature, and sports."),
    (3, "Part III: Simple Arithmetic, Mental Ability & Observation Skills (10 Marks)",
     "Simple Arithmetic (5 Marks), Mental Ability and Observation Skills (5 Marks)."),
    (4, "Part IV: General English (10 Marks)",
     "Grammar (5 Marks) and Vocabulary (5 Marks)."),
    (5, "Part V: Regional Language – Malayalam/Kannada/Tamil (10 Marks)",
     "Regional language spelling, grammar, proverbs, and translations."),
]
add_syllabus(15, ldc_parts)

# ─── 5. Degree Level Preliminary Exam (ID:16) ────────────────────────────
degree_prelim_parts = [
    (1, "Part I: General Knowledge (65 Marks)",
     "History (10 Marks), Geography (5 Marks), Economics (5 Marks), Civics (5 Marks), Indian Constitution (5 Marks), Arts/Sports/Literature/Culture (10 Marks), Computer Science (5 Marks), Science and Technology (5 Marks), Current Affairs."),
    (2, "Part II: Simple Arithmetic, Mental Ability and Reasoning (20 Marks)",
     "Simple Arithmetic (10 Marks), Mental Ability (10 Marks)."),
    (3, "Part III: General English (20 Marks)",
     "Grammar (10 Marks) and Vocabulary (10 Marks)."),
    (4, "Part IV: Regional Language – Malayalam/Kannada/Tamil (10 Marks)",
     "Regional language proficiency."),
]
add_syllabus(16, degree_prelim_parts)

# ─── 6. Assistant Grade II (ID:17) ───────────────────────────────────────
ag2_parts = [
    (1, "Part I: General Knowledge (65 Marks)",
     "Same as Degree Level Preliminary Exam: History, Geography, Economics, Civics, Constitution, Arts/Sports, Computer Science, S&T."),
    (2, "Part II: Simple Arithmetic, Mental Ability and Reasoning (20 Marks)",
     "Simple Arithmetic and Reasoning."),
    (3, "Part III: General English (20 Marks)",
     "Grammar and Vocabulary."),
    (4, "Part IV: Regional Language – Malayalam/Kannada/Tamil (10 Marks)",
     "Regional language proficiency."),
]
add_syllabus(17, ag2_parts)

# ─── 7. Sub Inspector of Police SI (ID:18) ────────────────────────────────
si_parts = [
    (1, "Part I: General Knowledge (20 Marks)",
     "History (3 Marks), Geography (3 Marks), Economics (3 Marks), Kerala Governance (5 Marks), Life Science & Public Health (6 Marks)."),
    (2, "Part II: Current Affairs (5 Marks)",
     "Current affairs."),
    (3, "Part III: Simple Arithmetic, Mental Ability and Reasoning (10 Marks)",
     "Simple Arithmetic (5 Marks), Mental Ability (5 Marks)."),
    (4, "Part IV: General English (10 Marks)",
     "Grammar (5 Marks) and Vocabulary (5 Marks)."),
    (5, "Part V: Regional Language – Malayalam/Kannada/Tamil (10 Marks)",
     "Language proficiency."),
    (6, "Part VI: Special Topics including Indian Constitution (45 Marks)",
     "IPC Offences (5 Marks), CrPC Procedures (5 Marks), IT Act (5 Marks), RTI Act (3 Marks), Constitution (7 Marks), IT and Cyber Crimes (10 Marks), Basics of Human Psychology (10 Marks)."),
]
add_syllabus(18, si_parts)

# ─── 8. Junior Health Inspector (ID:22) ──────────────────────────────────
jhi_parts = [
    (1, "Part I: General Knowledge and Current Affairs (30 Marks)",
     "GK (20 Marks) and Current Affairs (10 Marks)."),
    (2, "Part II: Simple Arithmetic and Mental Ability (10 Marks)",
     "Arithmetic and Reasoning."),
    (3, "Part III: General English (10 Marks)",
     "English Grammar and Vocabulary."),
    (4, "Part IV: Regional Language (10 Marks)",
     "Regional Language."),
    (5, "Part V: Special Topics – Public Health and Sanitation (40 Marks)",
     "Communicable diseases, Maternal and child health, Environment sanitation, Food hygiene, Vital statistics, National Health Programmes, First Aid."),
]
add_syllabus(22, jhi_parts)

# ─── 9. HSST Computer Science (ID:33) ────────────────────────────────────
hsst_cs_parts = [
    (1, "Part I: General Knowledge and Current Affairs (10 Marks)",
     "GK and Current Affairs."),
    (2, "Part II: Simple Arithmetic and Mental Ability (5 Marks)",
     "Arithmetic and Reasoning."),
    (3, "Part III: General English and Regional Language (10 Marks)",
     "Grammar and Vocabulary; Regional language."),
    (4, "Part IV: Core Subject – Computer Science (75 Marks)",
     "Computer Fundamentals, OOP Languages, Data Structures, DBMS, Networking, Operating Systems, Software Engineering, Cybersecurity & AI."),
]
add_syllabus(33, hsst_cs_parts)
