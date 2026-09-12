"""
Canonical Kerala PSC MCQ format.

Official paper shape (LDC / LGS / Degree / Constable, etc.):
  - One stem
  - Exactly four choices labelled A, B, C, D
  - One correct letter
  - English papers use English options; Malayalam papers use Malayalam
    options (English names, years and technical terms are allowed)

This module is the single source of truth for cleaning stored JSON,
API output, and the study-feed payload so students always see a
stable OMR-style list during long practice sessions.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Any, Dict, List, Optional, Tuple

LETTERS = ('A', 'B', 'C', 'D')
MALAYALAM_RE = re.compile(r'[\u0D00-\u0D7F]')
LATIN_WORD_RE = re.compile(r'[A-Za-z]{3,}')
# "A) text", "(B) text", "[c] text", "D. text" — not match-lists like "A:3 B:4"
LETTER_PREFIX_RE = re.compile(
    r'^\s*(?:\(|\[)?\s*([A-Da-d])\s*(?:\)|\]|\.)\s+'
)
YEAR_OR_NUMBER_RE = re.compile(r'^\d{3,4}(?:\D|$)')
PURE_NUMBER_RE = re.compile(r'^\d+(?:\.\d+)?$')
MEASURE_RE = re.compile(
    r'(sq\.?\s*km|square\s*km|metres?|meters?|inches?|hectares?|bytes?|\bkg\b|\bcm\b|\bkm\b|രൂപ|percent|%)',
    re.I,
)
STEM_NUMBER_CUE_RE = re.compile(
    r'(year|when|distance|length|area|how many|how much|വർഷ|എന്ന്|അളവ്|ദൂരം|വില|ശതമാനം|established|born|died)',
    re.I,
)
ML_LETTER_PREFIX_RE = re.compile(r'^\s*[\[\(]?\s*[എബിസിഡി]\s*[\)\]]\s*')
GLUED_B_PREFIX_RE = re.compile(r'^b(?=[\u0D00-\u0D7F])')
ANSWER_LEAK_RE = re.compile(r'^\s*(?:answer|ans)\.?\s*[:\-]\s*', re.IGNORECASE)
# Two questions concatenated: "...?31. Next question"
MASHED_QUESTION_RE = re.compile(
    r'^(?P<first>.+?[?।.])\s*\d{1,3}\.\s+(?P<second>.+)$',
    re.DOTALL,
)
WHITESPACE_RE = re.compile(r'[ \t]+')
MATCH_LIST_RE = re.compile(
    r'^[A-D]\s*[:=\-]\s*\S+.+(?:[A-D]\s*[:=\-]\s*\S+)',
    re.IGNORECASE,
)
# "All/None of the above" must stay last or the sentence becomes nonsense.
ANCHOR_LAST_RE = re.compile(
    r'^(all of the above|none of the above|none of these|all the above|'
    r'both\s*\(?[a-d]\)?\s*(?:and|&)\s*\(?[a-d]\)?|'
    r'മേല്പ്പറഞ്ഞവയെല്ലാം|മേൽപ്പറഞ്ഞവയെല്ലാം|ഇവയെല്ലാം|ഇവയൊന്നുമല്ല|'
    r'മുകളിൽ\s*പറഞ്ഞ\s*എല്ലാം)',
    re.I,
)
META_OPTION_RE = ANCHOR_LAST_RE
PERSON_STEM_RE = re.compile(
    r'(?:^\s*(?:who|whom)\b|'
    r'\bwho\s+(?:is|was|were|invented|founded|wrote|authored|discovered|known)\b|'
    r'\bwhich\s+(?:person|leader|poet|author|king|queen|minister|founder|scientist)\b|'
    r'ആരാണ്|ആരായിരുന്നു|ആരുടെ)',
    re.I,
)
YEAR_STEM_RE = re.compile(
    r'\b(?:in which year|which year|when was|when did|in the year)\b|'
    r'ഏത്\s*വർഷ|വർഷം\s*ഏത്|ഏതു\s*വർഷ',
    re.I,
)
PLACE_STEM_RE = re.compile(
    r'\b(?:where\s+(?:is|was|did|do)|which\s+(?:place|district|state|country|city|river)|'
    r'capital of|located in)\b|'
    r'എവിടെ(?:യാണ്)?|തലസ്ഥാനം',
    re.I,
)
QUANTITY_STEM_RE = re.compile(
    r'\b(?:how many|how much|how long|how far|how high)\b|'
    r'എത്ര(?:യാണ്|യായിരുന്നു)?',
    re.I,
)
MONTH_RE = re.compile(
    r'(january|february|march|april|may|june|july|august|september|october|'
    r'november|december|ചിങ്ങം|കന്നി|തുലാം|വൃശ്ചികം|ധനു|മകരം|കുംഭം|'
    r'മീനം|മേടം|ഇടവം|മിഥുനം|കർക്കടകം)',
    re.I,
)


def _as_dict(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return {}
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    if isinstance(raw, dict):
        # Nested shapes seen in older imports
        if 'options_list' in raw and isinstance(raw['options_list'], dict):
            return dict(raw['options_list'])
        if set(k.upper() for k in raw.keys()) <= {'OPTIONS', 'A', 'B', 'C', 'D'} and 'options' in raw:
            inner = raw.get('options')
            if isinstance(inner, dict):
                return dict(inner)
        return dict(raw)
    if isinstance(raw, (list, tuple)):
        out = {}
        for idx, val in enumerate(raw[:4]):
            out[LETTERS[idx]] = val
        return out
    return {}


def clean_option_text(value: Any) -> str:
    text = '' if value is None else str(value)
    text = text.replace('\u00a0', ' ').replace('\r', ' ').strip()
    text = WHITESPACE_RE.sub(' ', text)
    text = ANSWER_LEAK_RE.sub('', text).strip()
    text = ML_LETTER_PREFIX_RE.sub('', text).strip()
    text = GLUED_B_PREFIX_RE.sub('', text).strip()
    text = re.sub(r'^[\-\–—]\s+', '', text).strip()

    if MATCH_LIST_RE.match(text):
        return text.strip()

    prefix = LETTER_PREFIX_RE.match(text)
    if prefix:
        remainder = text[prefix.end():].strip()
        # Keep original if stripping would wipe a legitimate short token
        if remainder and remainder.upper() not in LETTERS:
            text = remainder

    return text.strip()


def clean_question_text(value: Any) -> str:
    text = '' if value is None else str(value)
    text = text.replace('\u00a0', ' ').strip()
    mashed = MASHED_QUESTION_RE.match(text)
    if mashed:
        first = mashed.group('first').strip()
        second = mashed.group('second').strip()
        # Only split when the second chunk looks like another full question
        if len(first) >= 8 and len(second) >= 8 and (
            second.endswith('?') or MALAYALAM_RE.search(second)
        ):
            text = first
    return WHITESPACE_RE.sub(' ', text).strip()


def normalize_options(raw: Any) -> Dict[str, str]:
    """Return exactly {A,B,C,D} with cleaned values (empty string if missing)."""
    source = _as_dict(raw)
    mapped: Dict[str, str] = {}

    index_aliases = {
        '0': 'A', '1': 'B', '2': 'C', '3': 'D',
        'OPTION_A': 'A', 'OPTION_B': 'B', 'OPTION_C': 'C', 'OPTION_D': 'D',
        'OPT_A': 'A', 'OPT_B': 'B', 'OPT_C': 'C', 'OPT_D': 'D',
    }

    for key, val in source.items():
        letter = str(key).strip().upper()
        letter = index_aliases.get(letter, letter)
        if letter in LETTERS and letter not in mapped:
            mapped[letter] = clean_option_text(val)

    return {letter: mapped.get(letter, '') for letter in LETTERS}


def normalize_correct_answer(raw: Any, options: Optional[Dict[str, str]] = None) -> str:
    letter = str(raw or '').strip().upper()
    aliases = {'0': 'A', '1': 'B', '2': 'C', '3': 'D', 'OPTION_A': 'A', 'E': '', 'F': ''}
    letter = aliases.get(letter, letter)
    if letter in LETTERS:
        return letter
    if options:
        needle = clean_option_text(raw).lower()
        for key, val in options.items():
            if val and val.strip().lower() == needle:
                return key
    return letter if letter in LETTERS else ''


def option_list(options: Any) -> List[Dict[str, str]]:
    normalized = normalize_options(options)
    return [{'key': k, 'text': normalized[k]} for k in LETTERS]


def _has_malayalam(text: str) -> bool:
    return bool(MALAYALAM_RE.search(text or ''))


def _has_latin(text: str) -> bool:
    return bool(LATIN_WORD_RE.search(text or ''))


def _option_kind(text: str) -> str:
    value = (text or '').strip()
    if MEASURE_RE.search(value):
        return 'measure'
    if PURE_NUMBER_RE.match(value) or re.match(r'^\d{4}\b', value):
        return 'number'
    if _has_malayalam(value):
        return 'malayalam'
    return 'text'


def _has_heterogeneous_options(stem: str, values: List[str]) -> bool:
    kinds = [_option_kind(v) for v in values]
    unique = {k for k in kinds if k}
    if len(unique) >= 3:
        return True
    # A lone year/measure among prose choices is the shuffled-pool signature.
    if kinds.count('number') == 1 and kinds.count('text') + kinds.count('malayalam') >= 2:
        return True
    if kinds.count('measure') == 1 and kinds.count('text') + kinds.count('malayalam') >= 2:
        return True
    return False


def servability_issues(text: str, options: Any, correct_answer: Any) -> List[str]:
    """Structural + KPSC-medium checks. Empty list means the item is exam-ready."""
    issues: List[str] = []
    stem = clean_question_text(text)
    opts = normalize_options(options)
    answer = normalize_correct_answer(correct_answer, opts)

    if not stem or len(stem) < 8:
        issues.append('empty_stem')

    empty_keys = [k for k, v in opts.items() if not v]
    if empty_keys:
        issues.append('missing_options')

    values = [opts[k] for k in LETTERS if opts[k]]
    lowered = [v.lower() for v in values]
    if len(lowered) == 4 and len(set(lowered)) < 4:
        issues.append('duplicate_options')

    if answer not in LETTERS:
        issues.append('invalid_answer_letter')
    elif not opts.get(answer):
        issues.append('answer_missing_option')

    # English stem with a mixed Malayalam/English option bank is the
    # shuffled-pool corruption students reported. All-Malayalam options
    # on an English "what is the Malayalam word" item are allowed.
    if stem and _has_latin(stem) and not _has_malayalam(stem):
        ml_count = sum(1 for v in values if _has_malayalam(v))
        # English paper with a mixed 1–2 Malayalam choices is shuffled-pool
        # corruption. Four Malayalam choices on an English "Malayalam word for"
        # item are allowed.
        if 1 <= ml_count <= 3:
            issues.append('shuffled_language_options')
    elif stem and _has_malayalam(stem):
        ml_count = sum(1 for v in values if _has_malayalam(v))
        no_ml = sum(1 for v in values if v and not _has_malayalam(v))
        # Malayalam paper with a split bank (some ML, some unrelated English)
        # is the same shuffle bug. All-English names/years on an ML stem are OK.
        if 1 <= ml_count <= 3 and no_ml >= 1:
            issues.append('shuffled_language_options')

    if len(values) == 4 and _has_heterogeneous_options(stem, values):
        issues.append('heterogeneous_options')

    leaked = [k for k, v in opts.items() if ANSWER_LEAK_RE.match(v or '')]
    if leaked:
        issues.append('answer_leaked_in_option')

    if logical_answer_mismatch(stem, opts, answer):
        issues.append('answer_key_mismatch')

    return issues


def _expected_option_kinds(stem: str) -> Optional[set]:
    """What kind of answer the stem is asking for, or None if ambiguous."""
    if YEAR_STEM_RE.search(stem):
        return {'number', 'measure'}
    if QUANTITY_STEM_RE.search(stem):
        return {'number', 'measure'}
    if PLACE_STEM_RE.search(stem):
        return {'text', 'malayalam'}
    if PERSON_STEM_RE.search(stem):
        return {'text', 'malayalam'}
    return None


def _kind_matches_expected(kind: str, text: str, expected: set) -> bool:
    if kind in expected:
        return True
    if 'number' in expected and (YEAR_OR_NUMBER_RE.match(text or '') or MONTH_RE.search(text or '')):
        return True
    return False


def logical_answer_mismatch(stem: str, options: Any, correct_answer: Any) -> bool:
    """True when the marked key is the wrong *type* for the stem, and a better-typed option exists.

    Conservative: never flags a uniformly-typed option bank (all years, all names).
    """
    opts = normalize_options(options)
    answer = normalize_correct_answer(correct_answer, opts)
    if answer not in LETTERS:
        return False
    correct_text = opts.get(answer, '')
    if not correct_text or META_OPTION_RE.match(correct_text.strip()):
        return False

    expected = _expected_option_kinds(stem)
    if not expected:
        return False

    correct_kind = _option_kind(correct_text)
    if _kind_matches_expected(correct_kind, correct_text, expected):
        return False

    other_matches = any(
        _kind_matches_expected(_option_kind(opts[k]), opts[k], expected)
        for k in LETTERS
        if k != answer and opts.get(k) and not META_OPTION_RE.match(opts[k].strip())
    )
    return other_matches


def shuffle_options(
    options: Any,
    correct_answer: Any,
    *,
    user_id: int = 0,
    question_id: int = 0,
    salt: int = 0,
) -> Tuple[Dict[str, str], str]:
    """Deterministic per-user A–D shuffle. 'All/None of the above' stays last."""
    opts = normalize_options(options)
    answer = normalize_correct_answer(correct_answer, opts)
    movable: List[Tuple[str, str]] = []
    anchored: List[Tuple[str, str]] = []
    for key in LETTERS:
        pair = (key, opts[key])
        if ANCHOR_LAST_RE.match((opts[key] or '').strip()):
            anchored.append(pair)
        else:
            movable.append(pair)

    seed_src = f"{int(user_id or 0)}:{int(question_id or 0)}:{int(salt or 0)}"
    rng = random.Random(int(hashlib.sha256(seed_src.encode()).hexdigest()[:16], 16))
    rng.shuffle(movable)
    ordered = movable + anchored
    shuffled = {LETTERS[i]: ordered[i][1] for i in range(min(4, len(ordered)))}
    correct_text = opts.get(answer, '')
    new_correct = answer
    for key, val in shuffled.items():
        if val == correct_text:
            new_correct = key
            break
    return shuffled, new_correct


def present_mcq(
    text: Any,
    options: Any,
    correct_answer: Any,
    explanation: str = '',
    *,
    user_id: int = 0,
    question_id: int = 0,
    salt: int = 0,
    shuffle: bool = True,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    opts = normalize_options(options)
    answer = normalize_correct_answer(correct_answer, opts)
    if shuffle:
        opts, answer = shuffle_options(
            opts, answer, user_id=user_id, question_id=question_id, salt=salt,
        )
    payload = {
        'text': clean_question_text(text),
        'options': opts,
        'correct_answer': answer,
        'explanation': (explanation or '').strip(),
    }
    if extra:
        payload.update(extra)
    return payload


def grade_selected_option(
    selected: Any,
    options: Any,
    correct_answer: Any,
    *,
    user_id: int = 0,
    question_id: int = 0,
    salt: int = 0,
    shuffle: bool = True,
) -> Tuple[bool, str]:
    """Compare the letter the student tapped with the letter they were shown."""
    selected_letter = str(selected or '').strip().upper()
    if shuffle:
        _, displayed = shuffle_options(
            options, correct_answer, user_id=user_id, question_id=question_id, salt=salt,
        )
    else:
        opts = normalize_options(options)
        displayed = normalize_correct_answer(correct_answer, opts)
    if selected_letter in ('', 'S', 'X'):
        return False, displayed
    return selected_letter == displayed, displayed


def selected_to_canonical(
    selected: Any,
    options: Any,
    correct_answer: Any,
    *,
    user_id: int = 0,
    question_id: int = 0,
    salt: int = 0,
    shuffle: bool = True,
) -> str:
    """Map the letter the student tapped back to the stored A–D key."""
    selected_letter = str(selected or '').strip().upper()
    if selected_letter in ('', 'S', 'X') or selected_letter not in LETTERS:
        return selected_letter if selected_letter else 'S'
    if not shuffle:
        return selected_letter
    opts = normalize_options(options)
    shuffled, _displayed = shuffle_options(
        opts, correct_answer, user_id=user_id, question_id=question_id, salt=salt,
    )
    text = shuffled.get(selected_letter, '')
    for key, val in opts.items():
        if val == text:
            return key
    return selected_letter


def interleave_reviews(fresh: List[Any], reviews: List[Any]) -> List[Any]:
    """Two new items, then one review — so a miss comes back a little later."""
    out: List[Any] = []
    i = j = 0
    while i < len(fresh) or j < len(reviews):
        if i < len(fresh):
            out.append(fresh[i])
            i += 1
        if i < len(fresh):
            out.append(fresh[i])
            i += 1
        if j < len(reviews):
            out.append(reviews[j])
            j += 1
    return out


def is_servable(text: str, options: Any, correct_answer: Any) -> bool:
    return not servability_issues(text, options, correct_answer)


def format_question_payload(
    text: str,
    options: Any,
    correct_answer: Any,
    explanation: str = '',
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    opts = normalize_options(options)
    payload = {
        'text': clean_question_text(text),
        'options': opts,
        'correct_answer': normalize_correct_answer(correct_answer, opts),
        'explanation': (explanation or '').strip(),
    }
    if extra:
        payload.update(extra)
    return payload


def apply_to_question(question) -> List[str]:
    """Normalize a Question model instance in memory. Returns issues after clean."""
    opts = normalize_options(question.options)
    question.text = clean_question_text(question.text)
    question.options = opts
    question.correct_answer = normalize_correct_answer(question.correct_answer, opts)
    return servability_issues(question.text, question.options, question.correct_answer)
