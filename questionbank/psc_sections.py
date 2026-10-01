"""
Kerala PSC paper sections.

Maps fine-grained Topic names onto the official syllabus parts for each exam
(History, Maths, Malayalam, …) so practice and weak-area focus follow the
real OMR paper instead of a flat topic list.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .syllabus_db import SYLLABUS_DATABASE, resolve_exam_slug

SECTION_COLORS = {
    'history': '#B45309',
    'geography': '#0F766E',
    'economics': '#0369A1',
    'constitution-and-polity': '#7C3AED',
    'facts-about-kerala': '#DC2626',
    'facts-about-india': '#C2410C',
    'biology-and-public-health': '#15803D',
    'public-health': '#16A34A',
    'physics': '#1D4ED8',
    'chemistry': '#9333EA',
    'science': '#2563EB',
    'arts-culture-literature-sports': '#DB2777',
    'computer': '#4F46E5',
    'important-laws': '#334155',
    'vocational-agriculture-topics': '#65A30D',
    'maths': '#2563EB',
    'english': '#7C3AED',
    'malayalam': '#D97706',
    'daily-current-affairs': '#059669',
    'fire-and-rescue-special-topics': '#E11D48',
    'ksrtc-conductor-special-topics': '#EA580C',
}

SECTION_ML = {
    'history': 'ചരിത്രം',
    'geography': 'ഭൂമിശാസ്ത്രം',
    'economics': 'സാമ്പത്തികശാസ്ത്രം',
    'constitution-and-polity': 'ഭരണഘടനയും ഭരണവും',
    'facts-about-kerala': 'കേരളം',
    'facts-about-india': 'ഇന്ത്യ',
    'biology-and-public-health': 'ജീവശാസ്ത്രം / ആരോഗ്യം',
    'public-health': 'പൊതുജനാരോഗ്യം',
    'physics': 'ഭൗതികശാസ്ത്രം',
    'chemistry': 'രസതന്ത്രം',
    'science': 'ശാസ്ത്രം',
    'arts-culture-literature-sports': 'കല / സാഹിത്യം / കായികം',
    'computer': 'കമ്പ്യൂട്ടർ',
    'important-laws': 'പ്രധാന നിയമങ്ങൾ',
    'vocational-agriculture-topics': 'കൃഷി',
    'maths': 'ഗണിതം',
    'english': 'ഇംഗ്ലീഷ്',
    'malayalam': 'മലയാളം',
    'daily-current-affairs': 'സമകാലികം',
    'fire-and-rescue-special-topics': 'ഫയർ & റെസ്‌ക്യൂ',
    'ksrtc-conductor-special-topics': 'KSRTC സ്‌പെഷ്യൽ',
}

# Most specific first.
CLASSIFY_RULES: List[Tuple[str, Tuple[str, ...]]] = [
    ('ksrtc-conductor-special-topics', ('ksrtc', 'conductor duty', 'motor vehicles act')),
    ('fire-and-rescue-special-topics', ('fire and rescue', 'fire fighting', 'fireman', 'rescue officer')),
    ('vocational-agriculture-topics', ('agriculture', 'crop', 'irrigation', 'farming', 'കൃഷി', 'paddy', 'coconut')),
    ('malayalam', ('malayalam', 'regional language', 'tamil', 'kannada', 'പദശുദ്ധി', 'വാക്യശുദ്ധി', 'ഒറ്റപ്പദം', 'പഴഞ്ചൊല്ല്', 'സന്ധി', 'സമാസം')),
    ('english', ('english', 'grammar', 'tense', 'voice', 'speech', 'synonym', 'antonym', 'vocabulary', 'spelling', 'preposition', 'comprehension', 'idiom')),
    ('maths', ('arithmetic', 'math', 'maths', 'mental ability', 'reasoning', 'hcf', 'lcm', 'bodmas', 'fraction', 'ratio', 'proportion', 'interest', 'average', 'algebra', 'geometry', 'mensuration', 'simplification', 'percentage', 'profit', 'loss', 'time & work', 'time and work', 'speed', 'distance', 'number series', 'coding')),
    ('daily-current-affairs', ('current affairs', 'current event', 'in news', 'awards', 'observance', 'latest news')),
    ('computer', ('computer', 'internet', 'ms office', 'hardware', 'software', 'windows', 'email')),
    ('important-laws', ('important law', 'rti', 'pocso', 'consumer protection', 'domestic violence', 'it act')),
    ('facts-about-kerala', ('kerala', 'renaissance', 'travancore', 'cochin', 'malabar', 'malayali', 'onam', 'keralolpathi', 'temple entry')),
    ('public-health', ('public health', 'hygiene', 'first aid', 'nutrition', 'communicable', 'vaccination', 'sanitation')),
    ('biology-and-public-health', ('biology', 'botany', 'zoology', 'physiology', 'human body', 'cell ', 'photosynthesis')),
    ('physics', ('physics', 'force', 'motion', 'optics', 'heat', 'light', 'magnetism', 'ohm', 'newton')),
    ('chemistry', ('chemistry', 'atom', 'acid', 'element', 'compound', 'periodic', 'organic')),
    ('science', ('science', 'scert', 'scientific')),
    ('constitution-and-polity', ('constitution', 'polity', 'preamble', 'fundamental right', 'parliament', 'panchayat', 'governance', 'directive principle', 'president', 'governor')),
    ('geography', ('geography', 'river', 'soil', 'climate', 'mountain', 'monsoon', 'plateau', 'ocean')),
    ('economics', ('economic', 'budget', 'gdp', 'five year', 'gst', 'planning commission', 'niti', 'inflation', 'poverty')),
    ('history', ('history', 'freedom', 'revolt', 'movement', 'mughal', 'british', 'war of', 'dynasty', 'independence')),
    ('arts-culture-literature-sports', ('arts', 'culture', 'literature', 'sports', 'cinema', 'music', 'dance', 'festival')),
    ('facts-about-india', ('facts about india', 'india', 'indian ', 'national ')),
]

# When an exam paper groups finer subjects into one part.
SECTION_PARENTS = {
    'physics': ['science'],
    'chemistry': ['science'],
    'biology-and-public-health': ['science', 'public-health'],
    'public-health': ['science', 'biology-and-public-health'],
    'history': ['facts-about-india'],
    'geography': ['facts-about-india'],
    'economics': ['facts-about-india'],
    'constitution-and-polity': ['facts-about-india'],
    'arts-culture-literature-sports': ['facts-about-india', 'daily-current-affairs'],
    'computer': ['facts-about-india', 'science'],
    'important-laws': ['facts-about-india', 'constitution-and-polity'],
    'facts-about-kerala': ['facts-about-india'],
}


def section_key(name: str) -> str:
    text = re.sub(r'[^a-z0-9]+', '-', (name or '').lower()).strip('-')
    aliases = {
        'mathematics': 'maths',
        'simple-arithmetic-mental-ability': 'maths',
        'simple-arithmetic': 'maths',
        'general-english': 'english',
        'regional-language': 'malayalam',
        'regional-language-malayalam-kannada-tamil': 'malayalam',
        'current-affairs': 'daily-current-affairs',
        'constitution': 'constitution-and-polity',
        'polity': 'constitution-and-polity',
        'indian-constitution': 'constitution-and-polity',
        'general-science': 'science',
        'facts-about-kerala-renaissance': 'facts-about-kerala',
    }
    return aliases.get(text, text)


def classify_topic(name: str, sub_topic: str = '') -> str:
    blob = f"{name or ''} {sub_topic or ''}".lower()
    if not blob.strip():
        return 'facts-about-india'
    for key, needles in CLASSIFY_RULES:
        if any(needle in blob for needle in needles):
            return key
    return 'facts-about-india'


def classify_label(key: str) -> str:
    mapping = {
        'history': 'History',
        'geography': 'Geography',
        'economics': 'Economics',
        'constitution-and-polity': 'Constitution and Polity',
        'facts-about-kerala': 'Facts About Kerala',
        'facts-about-india': 'Facts About India',
        'biology-and-public-health': 'Biology and Public Health',
        'public-health': 'Public Health',
        'physics': 'Physics',
        'chemistry': 'Chemistry',
        'science': 'Science',
        'arts-culture-literature-sports': 'Arts Culture Literature Sports',
        'computer': 'Computer',
        'important-laws': 'Important Laws',
        'vocational-agriculture-topics': 'Vocational Agriculture Topics',
        'maths': 'Maths',
        'english': 'English',
        'malayalam': 'Malayalam',
        'daily-current-affairs': 'Daily Current Affairs',
        'fire-and-rescue-special-topics': 'Fire and Rescue Special Topics',
        'ksrtc-conductor-special-topics': 'KSRTC Conductor Special Topics',
    }
    return mapping.get(key, key.replace('-', ' ').title())


def exam_blueprint(exam=None) -> Dict[str, Any]:
    slug = None
    if exam is not None:
        slug = resolve_exam_slug(getattr(exam, 'slug', None)) or resolve_exam_slug(getattr(exam, 'name', None))
    if not slug:
        slug = 'ldc-lgs-august-2026'
    data = SYLLABUS_DATABASE.get(slug) or SYLLABUS_DATABASE['ldc-lgs-august-2026']
    return {
        'slug': slug,
        'name': data.get('name') or (getattr(exam, 'name', None) if exam is not None else 'Kerala PSC'),
        'total_marks': data.get('total_marks', 100),
        'duration_minutes': data.get('duration_minutes', 75),
        'negative_marking': data.get('negative_marking', 0),
        'medium': data.get('medium', ''),
        'syllabus': list(data.get('syllabus') or []),
    }


def assign_topic_to_exam_section(topic_name: str, syllabus_rows: List[Dict[str, Any]], sub_topic: str = '') -> Optional[str]:
    """Return the official syllabus topic title this DB topic belongs to."""
    exam_keys = [(section_key(row.get('topic', '')), row.get('topic', '')) for row in syllabus_rows if row.get('topic')]
    names = [section_key(topic_name), section_key(sub_topic)]
    names = [name for name in names if name]
    # Trade and lab papers store the syllabus title as the topic name.
    # Match that before the general classifier, which otherwise files unknown
    # titles under Facts About India.
    for key, title in sorted(exam_keys, key=lambda item: len(item[0]), reverse=True):
        if not key:
            continue
        for name in names:
            if name == key or (len(key) >= 12 and key in name):
                return title
    canonical = classify_topic(topic_name, sub_topic)
    for key, title in exam_keys:
        if key == canonical:
            return title
        if canonical and key and (canonical in key or key in canonical):
            return title
    for parent in SECTION_PARENTS.get(canonical, []):
        for key, title in exam_keys:
            if key == parent or parent in key or key in parent:
                return title
    return None


# Chapters that must stay inside their subject. The first match wins.
# A heading like "Chemistry — Acids, Bases & Salts" is also kept as its own
# chapter under Chemistry, even when it is not listed here.
SUBDIVISIONS: Dict[str, List[Tuple[str, str, Tuple[str, ...]]]] = {
    'chemistry': [
        ('elements-and-periodic-table', 'Elements and Periodic Table', ('periodic', 'element', 'isotope', 'atomic')),
        ('acids-bases-and-salts', 'Acids, Bases and Salts', ('acid', 'alkali', 'bases', 'salts')),
        ('compounds-and-reactions', 'Compounds and Reactions', ('compound', 'organic', 'oxidation', 'chemical reaction', 'mole')),
        ('metals-and-non-metals', 'Metals and Non-metals', ('non-metal', 'metallurgy', 'alloy', 'reactivity series')),
    ],
    'physics': [
        ('motion-force-and-laws', 'Motion, Force and Laws', ('motion', 'newton', 'gravitation', 'force and')),
        ('heat-and-energy', 'Heat and Energy', ('heat', 'thermodynamic', 'temperature')),
        ('light-and-sound', 'Light and Sound', ('optic', 'sound', 'light')),
        ('electricity-and-magnetism', 'Electricity and Magnetism', ('electric', 'magnet', 'ohm')),
    ],
    'biology-and-public-health': [
        ('human-body', 'Human Body', ('human body', 'physiology', 'heart', 'blood', 'digestive', 'anatomy')),
        ('plants', 'Plant Kingdom', ('plant', 'photosynthesis', 'botany')),
        ('diseases-and-health', 'Diseases and Public Health', ('disease', 'pathogen', 'vaccine', 'vitamin', 'nutrition', 'hygiene')),
        ('cells-and-classification', 'Cells and Classification', ('classification', 'taxonomy', 'cell')),
    ],
    'public-health': [
        ('diseases-and-health', 'Diseases and Public Health', ('disease', 'vaccine', 'hygiene', 'nutrition', 'sanitation')),
    ],
    'maths': [
        ('number-system', 'Number System', ('number', 'hcf', 'lcm', 'fraction', 'simplification', 'bodmas')),
        ('percentage-and-profit', 'Percentage and Profit', ('percentage', 'profit', 'loss', 'discount')),
        ('ratio-and-interest', 'Ratio and Interest', ('ratio', 'proportion', 'interest', 'average')),
        ('time-and-work', 'Time and Work', ('time and work', 'time & work', 'speed', 'distance', 'mensuration')),
        ('reasoning', 'Reasoning', ('reasoning', 'series', 'coding', 'mental ability')),
    ],
    'history': [
        ('ancient-and-medieval', 'Ancient and Medieval', ('ancient', 'medieval', 'mughal', 'dynasty')),
        ('freedom-movement', 'Freedom Movement', ('freedom', 'independence', 'gandhi', 'revolt', 'national movement')),
    ],
    'geography': [
        ('physical-geography', 'Physical Geography', ('river', 'mountain', 'climate', 'soil', 'monsoon', 'ocean')),
        ('indian-geography', 'Indian Geography', ('india', 'indian')),
        ('kerala-geography', 'Kerala Geography', ('kerala',)),
    ],
    'constitution-and-polity': [
        ('preamble-and-rights', 'Preamble and Rights', ('preamble', 'fundamental right', 'directive principle')),
        ('union-and-state', 'Union and State', ('parliament', 'president', 'governor', 'panchayat')),
    ],
    'facts-about-kerala': [
        ('renaissance', 'Kerala Renaissance', ('renaissance', 'reform', 'sree narayana', 'chattampi')),
        ('kerala-history', 'Kerala History', ('travancore', 'cochin', 'malabar', 'temple entry')),
        ('kerala-culture', 'Kerala Culture', ('onam', 'kathakali', 'festival', 'culture')),
    ],
    'english': [
        ('grammar', 'Grammar', ('tense', 'voice', 'speech', 'preposition', 'article')),
        ('vocabulary', 'Vocabulary', ('synonym', 'antonym', 'vocabulary', 'spelling', 'idiom')),
    ],
    'malayalam': [
        ('grammar', 'Grammar', ('സന്ധി', 'സമാസം', 'വാക്യശുദ്ധി', 'പദശുദ്ധി')),
    ],
    'computer': [
        ('hardware-and-software', 'Hardware and Software', ('hardware', 'software', 'windows', 'ms office')),
        ('internet', 'Internet', ('internet', 'email', 'network')),
    ],
    'important-laws': [
        ('rights-and-protection', 'Rights and Protection Laws', ('rti', 'pocso', 'consumer', 'domestic violence')),
    ],
    'vocational-agriculture-topics': [
        ('crops', 'Crops', ('paddy', 'coconut', 'crop', 'irrigation')),
    ],
    'daily-current-affairs': [
        ('kerala-and-india', 'Kerala and India', ('kerala', 'india', 'award', 'appointment')),
    ],
    'arts-culture-literature-sports': [
        ('arts-and-culture', 'Arts and Culture', ('dance', 'music', 'cinema', 'festival', 'kathakali')),
        ('literature', 'Literature', ('literature', 'poet', 'novel')),
        ('sports', 'Sports', ('sport', 'olympic', 'games')),
    ],
}


def split_heading(name: str) -> Tuple[str, str]:
    text = (name or '').strip()
    for sep in (' — ', ' – ', ' - '):
        if sep in text:
            left, right = text.split(sep, 1)
            return left.strip(), right.strip()
    return text, ''


def rules_for_section(section_title: str) -> List[Tuple[str, str, Tuple[str, ...]]]:
    key = section_key(section_title)
    sources = [key]
    for child, parents in SECTION_PARENTS.items():
        if any(section_key(parent) == key or parent == key for parent in parents):
            sources.append(child)
    ordered: List[Tuple[str, str, Tuple[str, ...]]] = []
    seen = set()
    for source in sources:
        for row in SUBDIVISIONS.get(source, []):
            if row[0] in seen:
                continue
            seen.add(row[0])
            ordered.append(row)
    return ordered


def _match_rule(blob: str, rules) -> Optional[Tuple[str, str]]:
    low = (blob or '').lower()
    for key, label, needles in rules:
        if any(needle in low for needle in needles):
            return key, label
    return None


def subdivision_for(topic_name: str, sub_topic: str, section_title: str) -> Tuple[str, str]:
    """Chapter key and label inside a subject. Unclassified questions stay in 'general'."""
    rules = rules_for_section(section_title)
    topic_name = topic_name or ''
    sub_topic = sub_topic or ''
    parent_key = section_key(section_title)

    if section_key(topic_name) == parent_key and not split_heading(sub_topic)[1]:
        matched = _match_rule(sub_topic, rules)
        if matched:
            return matched
        return 'general', section_title

    for raw in (topic_name, sub_topic):
        parent, child = split_heading(raw)
        if not child:
            continue
        if section_key(parent) != parent_key and parent_key not in section_key(parent) and section_key(parent) not in parent_key:
            classified = classify_topic(parent, child)
            if section_key(classified) != parent_key and parent_key not in SECTION_PARENTS.get(classified, []):
                continue
        matched = _match_rule(child, rules)
        if matched:
            return matched
        return section_key(child)[:60], child[:80]

    matched = _match_rule(f'{topic_name} {sub_topic}', rules)
    if matched:
        return matched
    return 'general', section_title


def belongs_to_section(topic_name: str, sub_topic: str, section_title: str, syllabus_rows: List[Dict[str, Any]]) -> bool:
    assigned = assign_topic_to_exam_section(topic_name or '', syllabus_rows, sub_topic or '')
    return bool(assigned) and assigned == section_title


def summarize_section(groups, section_title: str, syllabus_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fold question groups into chapters inside one subject.

    groups: (topic_id, topic_name, sub_topic, count)
    Every matching question is counted once, under a chapter or under general.
    """
    buckets: Dict[str, Dict[str, Any]] = {}
    total = 0
    for item in groups:
        topic_id, name, sub = item[0], item[1] or '', item[2] or ''
        count = int(item[3] if len(item) > 3 else 1)
        if not belongs_to_section(name, sub, section_title, syllabus_rows):
            continue
        key, label = subdivision_for(name, sub, section_title)
        bucket = buckets.setdefault(key, {'key': key, 'name': label, 'question_count': 0, 'pairs': []})
        bucket['question_count'] += count
        bucket['pairs'].append((topic_id, sub))
        total += count
    chapters = [row for row in buckets.values() if row['question_count'] > 0]
    has_specific = any(row['key'] != 'general' for row in chapters)
    for row in chapters:
        if row['key'] == 'general' and has_specific:
            row['name'] = 'Other questions'
        row.pop('pairs', None)
    chapters.sort(key=lambda row: (row['key'] == 'general', -row['question_count'], row['name']))
    if len(chapters) == 1 and chapters[0]['key'] == 'general':
        chapters = []
    return {'question_count': total, 'subdivisions': chapters}


def section_pairs(groups, section_title: str, syllabus_rows: List[Dict[str, Any]], subdivision: str = ''):
    """(topic_id, sub_topic) pairs whose questions belong in this subject or chapter."""
    wanted = (subdivision or '').strip()
    pairs = []
    for item in groups:
        topic_id, name, sub = item[0], item[1] or '', item[2] or ''
        if topic_id is None:
            continue
        if not belongs_to_section(name, sub, section_title, syllabus_rows):
            continue
        key, _label = subdivision_for(name, sub, section_title)
        if wanted and key != wanted:
            continue
        pairs.append((topic_id, sub))
    return pairs


def section_meta(title: str, marks: int = 0) -> Dict[str, Any]:
    key = section_key(title)
    return {
        'key': key,
        'title': title,
        'title_ml': SECTION_ML.get(key, ''),
        'marks': marks,
        'color': SECTION_COLORS.get(key, '#2E8B57'),
    }


def user_exam(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    profile = getattr(user, 'userprofile', None)
    if profile is None:
        return None
    exam = getattr(profile, 'primary_exam', None)
    if exam:
        return exam
    prefs = getattr(profile, 'preferred_exams', None)
    if prefs is not None:
        return prefs.first()
    return None
