"""
Management command: generate_current_affairs
--------------------------------------------
Calls the Gemini API (primary) or GLM-5.1 on Modal (backup) to generate
today's Current Affairs items for Kerala PSC aspirants and stores validated
results in the CurrentAffairs model.

Usage:
    python manage.py generate_current_affairs          # generates for today
    python manage.py generate_current_affairs --date 2025-01-15  # specific date
    python manage.py generate_current_affairs --force  # overwrite existing
"""

import os
import json
import logging
import requests
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

logger = logging.getLogger(__name__)

# ─── Prompt builder ──────────────────────────────────────────────────────────

def build_prompt(target_date: str) -> str:
    return f"""You are KPSC Master, an assistant that generates CURRENT AFFAIRS for Kerala PSC exam preparation.

Your task:
Return TODAY'S current affairs for Kerala PSC aspirants, focused on Kerala and India, with some International, Science, Economy and Sports coverage.

You MUST respond with VALID JSON ONLY. No markdown, no comments, no natural language outside JSON.

JSON SCHEMA (exact keys and types):

{{
  "date": "YYYY-MM-DD",
  "items": [
    {{
      "category": "kerala" | "india" | "international" | "science" | "economy" | "sports",
      "headline": "string, <= 140 characters, factual news title",
      "summary": "string, 1-2 sentences, <= 280 characters, concise and factual, no opinions",
      "source_url": "string or null, a credible public news URL if known, else null",
      "mcq": {{
        "question": "string, 1 PSC-style MCQ based on this news item",
        "options": [
          "string option A",
          "string option B",
          "string option C",
          "string option D"
        ],
        "correct_index": 0 | 1 | 2 | 3,
        "explanation": "string, 1-3 sentences explaining the answer in simple language"
      }}
    }}
  ]
}}

REQUIREMENTS:

1. DATE:
   - "date" must be {target_date} in the format "YYYY-MM-DD".

2. COUNT AND DISTRIBUTION:
   - Generate 10-15 total items.
   - Prioritize categories:
       - At least 4 items in "kerala"
       - At least 3 items in "india"
       - The rest distributed across "international", "science", "economy", "sports".
   - Each item must have exactly one MCQ.

3. CONTENT QUALITY:
   - All headlines and summaries must describe REALISTIC, PLAUSIBLE news events for {target_date} relevant to Kerala PSC aspirants.
   - Prefer actual Indian / Kerala governance, schemes, budgets, committees, appointments, indices, rankings, awards, science & tech developments, and major sports events.
   - Summaries must be neutral and factual, no opinions or hype.
   - Avoid celebrity gossip, crime sensationalism, or irrelevant content.

4. MCQ QUALITY:
   - MCQs must be directly answerable from the headline + summary content.
   - Each MCQ must:
       - Be single-correct (exactly one correct option).
       - Have 4 options in "options" array.
       - "correct_index" is the zero-based index (0 = first option).
       - "explanation" must clearly state why the correct option is correct.
   - Use PSC-style language (formal, exam-oriented, no slang).

5. CATEGORY MAPPING:
   - Use "kerala" for state-level news (Kerala government, projects, institutions, local awards, state indicators).
   - Use "india" for national-level news, schemes, RBI, Union Government, national indices, national appointments.
   - Use "international" for global events with relevance to India or world affairs.
   - Use "science" for science & technology, space, environment, health, new discoveries.
   - Use "economy" for budgets, GDP, inflation, trade, RBI policy, major financial news.
   - Use "sports" for major tournaments, records, wins, especially with Indian or Kerala players.

6. SOURCE URL:
   - If you know or can infer a likely public news URL, include it.
   - If not, set "source_url" to null, not an empty string.

7. JSON REQUIREMENTS:
   - Output MUST be a single JSON object matching the schema exactly.
   - No trailing commas.
   - No comments.
   - No additional keys outside the schema.
   - Do NOT wrap JSON in markdown fences (no ```).
   - If you are unsure about a fact, prefer to omit that item and generate another generic but realistic one.

Return ONLY the JSON object.
"""


# ─── LLM Callers ─────────────────────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """Call Google Gemini API. Returns raw text or raises on failure."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    resp = requests.post(url, json=payload, timeout=40)
    resp.raise_for_status()

    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return text


def call_glm_modal(prompt: str) -> str:
    """Call GLM-5.1-FP8 on Modal (OpenAI-compatible). Returns raw text or raises on failure."""
    api_key = os.environ.get('GLM_MODAL_API_KEY')
    if not api_key:
        raise ValueError("GLM_MODAL_API_KEY not set in environment")

    url = "https://api.us-west-2.modal.direct/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "zai-org/GLM-5.1-FP8",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=40)
    resp.raise_for_status()

    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return text


def fetch_current_affairs_text(prompt: str) -> tuple[str, str]:
    """
    Try Gemini first, fall back to GLM-5.1 on Modal.
    Returns (raw_text, provider_name).
    Raises RuntimeError if both fail.
    """
    # ── Primary: Gemini ──────────────────────────────────────────────────────
    try:
        text = call_gemini(prompt)
        logger.info("[current_affairs] Gemini succeeded.")
        return text, "gemini"
    except Exception as e:
        logger.error("[current_affairs][gemini] Failed: %s", e)

    # ── Backup: GLM-5.1 on Modal ─────────────────────────────────────────────
    try:
        text = call_glm_modal(prompt)
        logger.info("[current_affairs] GLM-5.1 (Modal) succeeded.")
        return text, "glm_modal"
    except Exception as e:
        logger.error("[current_affairs][glm_modal] Failed: %s", e)

    raise RuntimeError("all_llm_backends_failed")


# ─── Validation helpers ───────────────────────────────────────────────────────

VALID_CATEGORIES = {"kerala", "india", "international", "science", "economy", "sports"}


def validate_item(item: dict) -> bool:
    """Return True if item passes schema validation."""
    if not isinstance(item, dict):
        return False

    # Required top-level keys
    for key in ("category", "headline", "summary", "mcq"):
        if key not in item:
            return False

    if item["category"] not in VALID_CATEGORIES:
        return False

    if not isinstance(item["headline"], str) or len(item["headline"]) > 140:
        return False

    if not isinstance(item["summary"], str) or len(item["summary"]) > 280:
        return False

    # source_url: string or None
    su = item.get("source_url")
    if su is not None and not isinstance(su, str):
        return False

    # MCQ validation
    mcq = item["mcq"]
    if not isinstance(mcq, dict):
        return False
    for k in ("question", "options", "correct_index", "explanation"):
        if k not in mcq:
            return False
    if not isinstance(mcq["options"], list) or len(mcq["options"]) != 4:
        return False
    if not isinstance(mcq["correct_index"], int) or mcq["correct_index"] not in (0, 1, 2, 3):
        return False
    for opt in mcq["options"]:
        if not isinstance(opt, str):
            return False

    return True


def strip_markdown_fence(text: str) -> str:
    """Strip ```json ... ``` fences if the model added them despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (``` or ```json) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()
    return text


# ─── DB save ─────────────────────────────────────────────────────────────────

def save_items(items: list, pub_date: date, stdout, style) -> int:
    """Validate and save items. Returns count of saved records."""
    from questionbank.models import CurrentAffairs

    saved = 0
    for idx, item in enumerate(items):
        if not validate_item(item):
            stdout.write(style.WARNING(f"  [SKIP] item {idx} failed validation"))
            continue

        headline = item["headline"].strip()

        # Avoid duplicates for the same date
        if CurrentAffairs.objects.filter(title=headline, publication_date=pub_date).exists():
            stdout.write(style.WARNING(f"  [SKIP] duplicate: {headline[:60]}"))
            continue

        # Map category to psc_likelihood heuristic
        psc_map = {
            "kerala": "high",
            "india": "high",
            "economy": "medium",
            "international": "low",
            "science": "medium",
            "sports": "low",
        }

        source_url = item.get("source_url")
        # Normalise empty string → None
        if isinstance(source_url, str) and source_url.strip() == "":
            source_url = None

        CurrentAffairs.objects.create(
            title=headline,
            content=item["summary"],
            category=item["category"].capitalize(),
            publication_date=pub_date,
            psc_likelihood=psc_map.get(item["category"], "medium"),
            ai_summary=item["summary"],
            source_url=source_url,
            mcq=item["mcq"],
        )
        saved += 1
        stdout.write(style.SUCCESS(f"  [SAVED] {headline[:70]}"))

    return saved


# ─── Management Command ───────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        "Generate today's Current Affairs for Kerala PSC using Gemini (primary) "
        "or GLM-5.1 on Modal (fallback) and save to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Target date in YYYY-MM-DD format. Defaults to today (IST).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="If set, will NOT skip existing records for the same date (allows duplicates).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and parse LLM output but do NOT write to the database.",
        )

    def handle(self, *args, **options):
        # ── Resolve date ────────────────────────────────────────────────────
        if options["date"]:
            try:
                pub_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError("--date must be in YYYY-MM-DD format")
        else:
            pub_date = timezone.localdate()  # IST-aware

        target_date_str = pub_date.strftime("%Y-%m-%d")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== Generating Current Affairs for {target_date_str} ==="
        ))

        # ── Build prompt ─────────────────────────────────────────────────────
        prompt = build_prompt(target_date_str)

        # ── Call LLM router ──────────────────────────────────────────────────
        try:
            raw_text, provider = fetch_current_affairs_text(prompt)
        except RuntimeError:
            logger.error("[current_affairs] all_llm_backends_failed for date=%s", target_date_str)
            self.stdout.write(self.style.ERROR(
                "[ERROR] All LLM backends failed. No data written. Check logs."
            ))
            return

        self.stdout.write(f"  Provider used: {provider}")

        # ── Strip markdown fences if present ─────────────────────────────────
        cleaned = strip_markdown_fence(raw_text)

        # ── Parse JSON ───────────────────────────────────────────────────────
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                "[current_affairs] invalid_json_from_llm provider=%s error=%s text=%r",
                provider, e, cleaned[:400],
            )
            self.stdout.write(self.style.ERROR(
                f"[ERROR] JSON parse failed ({provider}): {e}\nRaw snippet: {cleaned[:300]}"
            ))
            # Optionally retry with the other provider
            self.stdout.write("  Retrying with alternate provider...")
            try:
                if provider == "gemini":
                    raw_text2, provider2 = call_glm_modal(prompt), "glm_modal"
                else:
                    raw_text2, provider2 = call_gemini(prompt), "gemini"
                cleaned = strip_markdown_fence(raw_text2)
                parsed = json.loads(cleaned)
                provider = provider2
                self.stdout.write(f"  Retry succeeded with: {provider}")
            except Exception as e2:
                logger.error("[current_affairs] retry also failed: %s", e2)
                self.stdout.write(self.style.ERROR("[ERROR] Retry also failed. No data written."))
                return

        # ── Extract items ─────────────────────────────────────────────────────
        if not isinstance(parsed, dict) or "items" not in parsed:
            self.stdout.write(self.style.ERROR("[ERROR] Parsed JSON missing 'items' key."))
            return

        items = parsed["items"]
        if not isinstance(items, list):
            self.stdout.write(self.style.ERROR("[ERROR] 'items' is not a list."))
            return

        self.stdout.write(f"  Received {len(items)} items from LLM.")

        # ── Dry-run mode ──────────────────────────────────────────────────────
        if options["dry_run"]:
            valid_count = sum(1 for it in items if validate_item(it))
            self.stdout.write(self.style.WARNING(
                f"  DRY RUN -- {valid_count}/{len(items)} items would pass validation. Nothing saved."
            ))
            return

        # ── Save to DB ────────────────────────────────────────────────────────
        saved = save_items(items, pub_date, self.stdout, self.style)
        self.stdout.write(self.style.SUCCESS(
            f"\n[OK] Done -- {saved}/{len(items)} items saved for {target_date_str}."
        ))
