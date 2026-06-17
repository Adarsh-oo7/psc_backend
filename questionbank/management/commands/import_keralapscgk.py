import re
import hashlib
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from questionbank.models import Question, Topic, Exam, ExamCategory


class Command(BaseCommand):
    help = "Ingests questions from keralapscgk.com - supports both MCQ and Q&A formats"

    def add_arguments(self, parser):
        parser.add_argument('--max-posts', type=int, default=150, help="Max number of posts to fetch")
        parser.add_argument('--label', type=str, default='Mock Test', help="Blogger label to filter posts")
        parser.add_argument('--dry-run', action='store_true', help="Dry run without saving to database")

    def handle(self, *args, **options):
        max_posts = options['max_posts']
        label = options['label']
        dry_run = options['dry_run']

        self.stdout.write(f"Starting ingestion from keralapscgk.com (Label: {label})...")

        encoded_label = requests.utils.quote(label)
        base_feed_url = f"https://www.keralapscgk.com/feeds/posts/default/-/{encoded_label}?alt=json"

        posts_fetched = 0
        questions_imported = 0
        duplicates_skipped = 0
        errors_count = 0
        start_index = 1
        page_size = 50

        general_psc_exam, _ = Exam.objects.get_or_create(
            name="General PSC (2025)",
            defaults={
                'year': 2025,
                'category': ExamCategory.objects.first() or ExamCategory.objects.create(name="PSC", order=1)
            }
        )

        exam_keywords_mapping = {
            'ldc': 'LD Clerk (LDC) (2025)',
            'clerk': 'LD Clerk (LDC) (2025)',
            'lgs': 'Last Grade Servant (LGS) (2025)',
            'servant': 'Last Grade Servant (LGS) (2025)',
            'police': 'Police Constable (2025)',
            'constable': 'Police Constable (2025)',
            'cpo': 'Civil Police Officer (CPO) (2025)',
            'si': 'Sub Inspector of Police (SI) (2025)',
            'inspector': 'Sub Inspector of Police (SI) (2025)',
            'assistant': 'Assistant / Junior Assistant (Various Depts.) (2025)',
            'driver': 'Driver (Light / Heavy) (2025)',
            'hsa': 'High School Assistant (HSA) (2025)',
        }

        skip_labels = {'Mock Test', 'Model Questions', 'Daily Quiz', 'Study Material'}

        while posts_fetched < max_posts:
            feed_url = f"{base_feed_url}&max-results={page_size}&start-index={start_index}"
            self.stdout.write(f"Fetching posts from: {feed_url}...")

            try:
                res = requests.get(feed_url, timeout=15)
                if res.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"Failed to fetch feed: HTTP {res.status_code}"))
                    break

                data = res.json()
                entries = data.get('feed', {}).get('entry', [])
                if not entries:
                    self.stdout.write("No more posts found in feed.")
                    break

                self.stdout.write(f"Processing {len(entries)} posts...")

                for entry in entries:
                    if posts_fetched >= max_posts:
                        break

                    post_title = entry.get('title', {}).get('$t', 'Mock Test Post')
                    html_content = entry.get('content', {}).get('$t', '')
                    categories = [cat.get('term') for cat in entry.get('category', [])]

                    safe_title = post_title.encode('ascii', errors='replace').decode('ascii')
                    self.stdout.write(f"\nParsing post: {safe_title}")

                    soup = BeautifulSoup(html_content, 'html.parser')

                    # --- Detect quiz format ---
                    # Format A: Modern MCQ with .single-question-container / .quiz-container
                    mcq_containers = soup.find_all(class_='single-question-container')
                    if not mcq_containers:
                        mcq_containers = soup.find_all(class_='quiz-container')

                    # Format B: Old santosh-button Q&A reveal format
                    santosh_inputs = soup.find_all('input', class_='santosh')

                    if not mcq_containers and not santosh_inputs:
                        self.stdout.write(self.style.WARNING("  No supported quiz format found. Skipping."))
                        continue

                    # Determine primary topic from categories
                    topic_name = label if label not in skip_labels else "General Knowledge"
                    for cat in categories:
                        if cat and cat not in skip_labels and cat != 'General Knowledge':
                            topic_name = cat
                            break

                    topic_slug = slugify(topic_name) or 'general-knowledge'
                    topic_obj = None
                    if not dry_run:
                        topic_obj, _ = Topic.objects.get_or_create(
                            slug=topic_slug,
                            defaults={'name': topic_name}
                        )

                    # Determine linked exams
                    linked_exams = [general_psc_exam]
                    title_lower = post_title.lower()
                    for keyword, exam_name in exam_keywords_mapping.items():
                        if keyword in title_lower:
                            try:
                                specific_exam = Exam.objects.get(name=exam_name)
                                linked_exams.append(specific_exam)
                            except Exam.DoesNotExist:
                                pass

                    parsed_questions = []

                    # ===========================
                    # FORMAT A: Modern MCQ parser
                    # ===========================
                    if mcq_containers:
                        self.stdout.write(f"  [Format A - MCQ] Found {len(mcq_containers)} containers.")
                        for container in mcq_containers:
                            q_name_div = container.find(class_='questionName') or container.find(class_='question')
                            if not q_name_div:
                                continue

                            question_text = q_name_div.get_text(strip=True)
                            question_text = re.sub(r'^\d+[\s\.\)]+', '', question_text).strip()

                            opt_container = container.find(class_='options-container') or container
                            opt_divs = opt_container.find_all(class_='label-div')

                            if len(opt_divs) < 2:
                                continue

                            options_dict = {}
                            correct_answer = 'A'
                            letters = ['A', 'B', 'C', 'D']

                            for opt_idx, opt_div in enumerate(opt_divs):
                                if opt_idx >= len(letters):
                                    break
                                letter = letters[opt_idx]
                                opt_text = opt_div.get_text(strip=True)
                                opt_text = re.sub(r'^[A-D][\s\.\)]+', '', opt_text).strip()
                                options_dict[letter] = opt_text
                                if 'correct' in opt_div.get('class', []):
                                    correct_answer = letter

                            if question_text and len(options_dict) >= 2:
                                parsed_questions.append({
                                    'text': question_text,
                                    'options': options_dict,
                                    'correct_answer': correct_answer,
                                })

                    # ================================================
                    # FORMAT B: Old santosh-button Q&A reveal parser
                    # ================================================
                    elif santosh_inputs:
                        self.stdout.write(f"  [Format B - Q&A] Found {len(santosh_inputs)} items.")
                        # Split HTML by <hr> tags to get individual Q&A blocks
                        blocks = re.split(r'<hr\s*/?>', html_content, flags=re.IGNORECASE)
                        for block in blocks:
                            block_soup = BeautifulSoup(block, 'html.parser')
                            btn = block_soup.find('input', class_='santosh')
                            if not btn:
                                continue

                            # Extract correct answer text from onclick attribute
                            onclick = btn.get('onclick', '')
                            answer_match = re.search(r'Answer\s*[-\u2013]\s*(.+?)["\')]', onclick)
                            if not answer_match:
                                continue
                            correct_text = answer_match.group(1).strip()
                            if not correct_text or len(correct_text) < 1:
                                continue

                            # Remove the button element to get clean question text
                            btn.decompose()
                            raw_text = block_soup.get_text(separator=' ', strip=True)
                            question_text = re.sub(r'^\d+[\s\.\)]+', '', raw_text).strip()
                            question_text = re.sub(r'\s+', ' ', question_text).strip()

                            if not question_text or len(question_text) < 8:
                                continue

                            # Create MCQ-style options with correct answer as A
                            short_correct = correct_text[:50]
                            options_dict = {
                                'A': correct_text,
                                'B': f'Not {short_correct}' if len(correct_text) > 2 else 'Option B',
                                'C': 'None of the above',
                                'D': 'All of the above',
                            }

                            parsed_questions.append({
                                'text': question_text,
                                'options': options_dict,
                                'correct_answer': 'A',
                            })

                    # ===========================
                    # SAVE ALL PARSED QUESTIONS
                    # ===========================
                    if not parsed_questions:
                        self.stdout.write(self.style.WARNING("  No parseable questions found. Skipping."))
                        continue

                    self.stdout.write(f"  Saving {len(parsed_questions)} questions...")

                    try:
                        with transaction.atomic():
                            for q_data in parsed_questions:
                                question_text = q_data['text']
                                options_dict = q_data['options']
                                correct_answer = q_data['correct_answer']

                                normalized = re.sub(r'[^\w\s]', '', question_text).lower().strip()
                                normalized = re.sub(r'\s+', ' ', normalized)
                                text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                                if Question.objects.filter(text_hash=text_hash).exists():
                                    duplicates_skipped += 1
                                    continue

                                if not dry_run:
                                    q_obj = Question.objects.create(
                                        text=question_text,
                                        options=options_dict,
                                        correct_answer=correct_answer,
                                        topic=topic_obj,
                                        sub_topic=topic_name,
                                        difficulty='medium',
                                        language='ml' if re.search(r'[\u0d00-\u0d7f]', question_text) else 'en',
                                        source='psc_official',
                                        status='approved',
                                        is_verified=True,
                                        verified=True,
                                        text_hash=text_hash
                                    )
                                    q_obj.exams.set(linked_exams)
                                else:
                                    safe_text = question_text[:60].encode('ascii', errors='replace').decode('ascii')
                                    safe_ans = str(options_dict.get(correct_answer, ''))[:30].encode('ascii', errors='replace').decode('ascii')
                                    self.stdout.write(f"    [DRY RUN] {safe_text}... | Ans {correct_answer}: {safe_ans}")

                                questions_imported += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  Error saving questions: {e}"))
                        errors_count += 1

                    posts_fetched += 1

                start_index += page_size

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching page at {start_index}: {e}"))
                break

        self.stdout.write(self.style.SUCCESS(
            f"\nIngestion Complete!\n"
            f"  - Posts fetched: {posts_fetched}\n"
            f"  - Questions imported: {questions_imported}\n"
            f"  - Duplicates skipped: {duplicates_skipped}\n"
            f"  - Errors encountered: {errors_count}"
        ))
