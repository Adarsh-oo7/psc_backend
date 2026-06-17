import os
import re
import json
import time
import hashlib
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from questionbank.models import Question, Topic, Exam, ExamCategory, PreviousYearPaper

class Command(BaseCommand):
    help = "Extracts Malayalam questions from legacy/garbled PDFs using Gemini API"

    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help="Path to the PDF file")
        parser.add_argument('--limit-pages', type=int, default=0, help="Limit the number of pages to process (0 for all)")
        parser.add_argument('--exam', type=str, default="LGS General Exam", help="Name of the exam to associate questions with")
        parser.add_argument('--year', type=int, default=2024, help="Year of the exam")
        parser.add_argument('--paper-title', type=str, help="Title of the PreviousYearPaper to link questions to")
        parser.add_argument('--approve-all', action='store_true', help="Set question status to approved directly")

    def handle(self, *args, **options):
        # 1. API Key Setup
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise CommandError("GEMINI_API_KEY environment variable is not set. Please add it to your psc_backend/.env file.")

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
        except ImportError:
            raise CommandError("google-generativeai is not installed. Please install it using: pip install google-generativeai")

        try:
            import pdfplumber
        except ImportError:
            raise CommandError("pdfplumber is not installed. Please install it using: pip install pdfplumber")

        pdf_path = options['pdf_path']
        limit_pages = options['limit_pages']
        exam_name = options['exam']
        year = options['year']
        paper_title = options.get('paper_title')
        approve_all = options['approve_all']

        if not os.path.exists(pdf_path):
            raise CommandError(f"PDF file not found at: {pdf_path}")

        # Get the default category and create/fetch the Exam
        exam_slug = slugify(exam_name)
        default_cat, _ = ExamCategory.objects.get_or_create(
            name="PSC Direct Recruitment", defaults={'order': 0}
        )
        exam_obj, _ = Exam.objects.get_or_create(
            slug=exam_slug,
            defaults={
                'name': exam_name,
                'category': default_cat,
                'duration_minutes': 75,
                'year': year
            }
        )

        paper_obj = None
        if paper_title:
            rel_pdf_path = os.path.join('pyq_papers', os.path.basename(pdf_path))
            paper_obj, _ = PreviousYearPaper.objects.get_or_create(
                title=paper_title,
                defaults={
                    'exam': exam_obj,
                    'year': year,
                    'pdf_file': rel_pdf_path
                }
            )

        # Build list of valid topics to feed to Gemini for classification
        topics = Topic.objects.all()
        topics_map = {t.slug: t for t in topics}
        topics_list_str = "\n".join([f"- {t.slug}: {t.name}" for t in topics])

        self.stdout.write(f"Reading PDF: {pdf_path}...")
        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(limit_pages, total_pages) if limit_pages > 0 else total_pages
            self.stdout.write(f"Processing {pages_to_process} out of {total_pages} pages...")

            for i in range(pages_to_process):
                text = pdf.pages[i].extract_text()
                if text:
                    pages_text.append((i + 1, text))

        model = genai.GenerativeModel('gemini-2.5-flash')
        general_topic, _ = Topic.objects.get_or_create(slug="general", defaults={"name": "General"})

        # Process page by page (or in small chunks of pages) to stay within token limits
        total_extracted = 0
        total_skipped = 0

        for page_num, raw_text in pages_text:
            self.stdout.write(f"Sending Page {page_num} to Gemini API for translation & extraction...")
            
            # Clean page text of standard headers
            cleaned_lines = []
            for line in raw_text.split('\n'):
                low = line.lower()
                if any(term in low for term in ["page", "kerala psc", "reg no", "register number", "maximum marks", "duration", "booklet", "space for rough work"]):
                    continue
                cleaned_lines.append(line)
            chunk_text = "\n".join(cleaned_lines)

            # Skip pages that are just empty space or table of contents
            if len(chunk_text.strip()) < 50:
                continue

            prompt = f"""
You are a professional Malayalam language translator and Kerala PSC exam expert.
The following text contains multiple choice questions from a Kerala PSC exam.
However, the Malayalam text in the PDF is garbled due to an old legacy ASCII font encoding (e.g. ML-TT font representation).
Examples:
- "LRu krpOÐvp]¤" -> "താഴെ പറയുന്നവയിൽ"
- "CÍ|pORa" -> "ഇന്ത്യയുടെ"
- "Ap¤ qL^|U" -> "അയൽ രാജ്യം"
- "AsæL¾fV JfV ?" -> "അതിർത്തി ഏത് ?"

Your task is to:
1. Reconstruct and clean the garbled Malayalam ASCII text into standard Malayalam Unicode text.
2. Extract all questions from the text block.
3. For each question, compile:
   - "question": Clean Malayalam Unicode question text.
   - "option_a": Option A in Malayalam.
   - "option_b": Option B in Malayalam.
   - "option_c": Option C in Malayalam.
   - "option_d": Option D in Malayalam.
   - "correct": The correct answer choice code ('A', 'B', 'C', or 'D') based on general knowledge or if there is an answer key mentioned.
   - "explanation": A 1-2 sentence explanation in Malayalam.
   - "topic_slug": Select the most appropriate topic slug from the list of valid topics below. If none match well, use "general".

Valid topic slugs:
{topics_list_str}

Text block to process:
---
{chunk_text}
---

Return ONLY a valid JSON array of objects with the structure:
[
  {{
    "question": "question text",
    "option_a": "option A",
    "option_b": "option B",
    "option_c": "option C",
    "option_d": "option D",
    "correct": "A|B|C|D",
    "explanation": "explanation",
    "topic_slug": "matched-topic-slug"
  }}
]
"""

            try:
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                raw_json = response.text.strip()
                # Clean up markdown if any
                if raw_json.startswith('```json'):
                    raw_json = raw_json[7:-3].strip()
                elif raw_json.startswith('```'):
                    raw_json = raw_json[3:-3].strip()

                questions_list = json.loads(raw_json)
                self.stdout.write(f"Page {page_num}: Extracted {len(questions_list)} questions from Gemini.")

                for item in questions_list:
                    q_text = item.get('question')
                    opt_a = item.get('option_a')
                    opt_b = item.get('option_b')
                    opt_c = item.get('option_c') or ''
                    opt_d = item.get('option_d') or ''
                    correct = item.get('correct', 'A').upper()
                    explanation = item.get('explanation') or ''
                    topic_slug = item.get('topic_slug', 'general')

                    if not q_text or not opt_a or not opt_b or not correct:
                        continue

                    # Retrieve matching topic
                    topic = topics_map.get(topic_slug, general_topic)

                    options_dict = {
                        'A': opt_a,
                        'B': opt_b,
                        'C': opt_c,
                        'D': opt_d
                    }

                    # Deduplication check using hash
                    normalized = re.sub(r'[^\w\s]', '', q_text).lower().strip()
                    normalized = re.sub(r'\s+', ' ', normalized)
                    if options_dict and isinstance(options_dict, dict):
                        opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options_dict.items()))
                        normalized = f"{normalized}||{opts_str}"
                    text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                    existing_q = Question.objects.filter(text_hash=text_hash).first()
                    if existing_q:
                        total_skipped += 1
                        if paper_obj:
                            paper_obj.questions.add(existing_q)
                        continue

                    # Create and save question
                    q = Question.objects.create(
                        text=q_text,
                        options=options_dict,
                        correct_answer=correct,
                        topic=topic,
                        difficulty='medium',
                        explanation=explanation,
                        language='ml',  # Set language to Malayalam!
                        source='psc_official',
                        verified=approve_all,
                        is_verified=approve_all,
                        status='approved' if approve_all else 'pending',
                        text_hash=text_hash
                    )
                    q.exams.add(exam_obj)
                    if paper_obj:
                        paper_obj.questions.add(q)
                    total_extracted += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing page {page_num}: {e}"))

            # Be nice to Gemini API limits
            time.sleep(2.0)

        self.stdout.write(self.style.SUCCESS(
            f"Completed PDF extraction! Saved: {total_extracted} questions | Skipped duplicates: {total_skipped}"
        ))
