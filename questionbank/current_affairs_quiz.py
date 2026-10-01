"""Build Current Affairs quiz questions from stored news MCQs."""

from __future__ import annotations

import json
from datetime import timedelta

from django.db import IntegrityError
from django.utils import timezone

from .kpsc_format import is_servable
from .models import CurrentAffairs, Exam, Question, Topic

LETTERS = ('A', 'B', 'C', 'D')


def parse_ca_mcq(raw) -> dict | None:
    mcq = raw
    if isinstance(mcq, str):
        try:
            mcq = json.loads(mcq)
        except json.JSONDecodeError:
            return None
    if not isinstance(mcq, dict):
        return None

    question = (mcq.get('question') or mcq.get('text') or '').strip()
    if not question:
        return None

    options_dict = {}
    options = mcq.get('options')
    if isinstance(options, dict):
        for key in LETTERS:
            value = str(options.get(key) or options.get(key.lower()) or '').strip()
            if value:
                options_dict[key] = value
    elif isinstance(options, list):
        for idx, value in enumerate(options[:4]):
            text = str(value or '').strip()
            if text:
                options_dict[LETTERS[idx]] = text

    if len(options_dict) < 4:
        return None

    correct_key = str(mcq.get('correct_answer') or '').strip().upper()[:1]
    if correct_key not in options_dict:
        index = mcq.get('correct_index')
        if isinstance(index, int) and 0 <= index < 4:
            correct_key = LETTERS[index]
    if correct_key not in options_dict:
        return None

    return {
        'question': question,
        'options_dict': options_dict,
        'correct_key': correct_key,
        'explanation': str(mcq.get('explanation') or '').strip(),
    }


def daily_ca_topic() -> Topic:
    topic = Topic.objects.filter(slug='daily-current-affairs').first()
    if topic:
        return topic
    topic = Topic.objects.filter(name__iexact='Daily Current Affairs').first()
    if topic:
        return topic
    return Topic.objects.create(name='Daily Current Affairs', slug='daily-current-affairs')


def ensure_question_for_ca(ca: CurrentAffairs, topic: Topic | None = None, exams=None) -> Question | None:
    parsed = parse_ca_mcq(getattr(ca, 'mcq', None))
    if not parsed:
        return None
    topic = topic or daily_ca_topic()
    existing = Question.objects.filter(text=parsed['question']).first()
    if existing:
        question = existing
    else:
        question = Question(
            text=parsed['question'],
            options=parsed['options_dict'],
            correct_answer=parsed['correct_key'],
            explanation=parsed['explanation'],
            topic=topic,
            language='en',
            source='ai_generated',
            status='approved',
            is_public=True,
            sub_topic=(ca.title or '')[:255],
        )
        try:
            question.save()
        except IntegrityError:
            question = Question.objects.filter(text=parsed['question']).first()
            if not question:
                return None
    if exams:
        question.exams.add(*exams)
    if not is_servable(question.text, question.options, question.correct_answer):
        return None
    if question.status != 'approved' or not question.is_public:
        return None
    return question


def questions_for_weekly_quiz(limit: int = 15):
    cutoff = timezone.localdate() - timedelta(days=10)
    items = CurrentAffairs.objects.filter(
        publication_date__gte=cutoff, is_published=True,
    ).order_by('-publication_date', '-id')
    questions = []
    seen = set()
    topic = daily_ca_topic()
    exams = list(Exam.objects.filter(slug__in=[
        'company-board-lgs', 'ldc-lgs-august-2026', 'village-field-assistant',
    ])[:8])

    for ca in items:
        question = ensure_question_for_ca(ca, topic=topic, exams=exams)
        if not question or question.id in seen:
            continue
        questions.append(question)
        seen.add(question.id)
        if len(questions) >= limit:
            return questions

    if len(questions) < 5:
        extra = (
            Question.objects.filter(
                topic=topic,
                status='approved',
                is_public=True,
            )
            .exclude(id__in=seen)
            .order_by('-id')[: limit - len(questions)]
        )
        questions.extend(list(extra))
    return questions
