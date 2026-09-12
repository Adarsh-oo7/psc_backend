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
    canonical = classify_topic(topic_name, sub_topic)
    exam_keys = [(section_key(row.get('topic', '')), row.get('topic', '')) for row in syllabus_rows]
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
