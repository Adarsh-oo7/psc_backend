import re
import hashlib
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from questionbank.models import Question, Topic, Exam, ExamCategory

class Command(BaseCommand):
    help = "Ingests multiple choice questions from keralapscgk.com feeds"

    def add_arguments(self, parser):
        parser.add_argument('--max-posts', type=int, default=150, help="Max number of posts to fetch")
        parser.add_argument('--label', type=str, default='Mock Test', help="Blogger label to filter posts")
        parser.add_argument('--dry-run', action='store_true', help="Execute dry-run without writing to database")

    def handle(self, *args, **options):
        max_posts = options['max_posts']
        label = options['label']
        dry_run = options['dry_run']

        self.stdout.write(f"Starting ingestion from keralapscgk.com (Label: {label})...")

        # Map labels to URL encoded format
        encoded_label = requests.utils.quote(label)
        base_feed_url = f"https://www.keralapscgk.com/feeds/posts/default/-/{encoded_label}?alt=json"

        posts_fetched = 0
        questions_imported = 0
        duplicates_skipped = 0
        errors_count = 0
        start_index = 1
        page_size = 50

        # General PSC exam to link questions to
        general_psc_exam, _ = Exam.objects.get_or_create(
            name="General PSC (2025)",
            defaults={
                'year': 2025,
                'category': ExamCategory.objects.first() or ExamCategory.objects.create(name="PSC", order=1)
            }
        )

        # Common exam keywords for mapping
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
                    
                    # Safe print title for Windows console
                    safe_title = post_title.encode('ascii', errors='replace').decode('ascii')
                    self.stdout.write(f"\nParsing post: {safe_title}")
                    
                    # Parse HTML quiz questions
                    soup = BeautifulSoup(html_content, 'html.parser')
                    question_containers = soup.find_all(class_='single-question-container')
                    
                    if not question_containers:
                        # Try fallback selectors (e.g. list structure or generic quiz wrappers)
                        question_containers = soup.find_all(class_='quiz-container')

                    if not question_containers:
                        self.stdout.write(self.style.WARNING("  No quiz questions format found in this post. Skipping."))
                        continue
                    
                    self.stdout.write(f"  Found {len(question_containers)} question containers.")

                    # Determine primary topic from categories/labels
                    topic_name = "General Knowledge"
                    for cat in categories:
                        if cat not in ['Mock Test', 'Model Questions', 'Daily Quiz', 'Study Material']:
                            topic_name = cat
                            break
                    
                    topic_slug = slugify(topic_name) or 'general-knowledge'
                    topic_obj = None
                    if not dry_run:
                        topic_obj, _ = Topic.objects.get_or_create(
                            slug=topic_slug,
                            defaults={'name': topic_name}
                        )

                    # Determine exams to link questions to
                    linked_exams = [general_psc_exam]
                    title_lower = post_title.lower()
                    for keyword, exam_name in exam_keywords_mapping.items():
                        if keyword in title_lower:
                            try:
                                specific_exam = Exam.objects.get(name=exam_name)
                                linked_exams.append(specific_exam)
                            except Exam.DoesNotExist:
                                pass

                    # Ingest questions under database transaction
                    try:
                        with transaction.atomic():
                            for q_idx, container in enumerate(question_containers, start=1):
                                # Extract question text
                                q_name_div = container.find(class_='questionName') or container.find(class_='question')
                                if not q_name_div:
                                    continue
                                
                                question_text = q_name_div.get_text(strip=True)
                                # Clean leading index numbers like "1.", "2)" if present
                                question_text = re.sub(r'^\d+[\s\.\)]+', '', question_text).strip()

                                # Extract options
                                opt_container = container.find(class_='options-container') or container
                                opt_divs = opt_container.find_all(class_='label-div')
                                
                                if len(opt_divs) < 2:
                                    continue

                                options_dict = {}
                                correct_answer = 'A'
                                letters = ['A', 'B', 'C', 'D', 'E', 'F']
                                
                                for opt_idx, opt_div in enumerate(opt_divs):
                                    if opt_idx >= len(letters):
                                        break
                                    letter = letters[opt_idx]
                                    opt_text = opt_div.get_text(strip=True)
                                    # Clean leading letter prefixes like "A)", "B."
                                    opt_text = re.sub(r'^[A-F][\s\.\)]+', '', opt_text).strip()
                                    
                                    options_dict[letter] = opt_text
                                    
                                    # Determine correct answer class
                                    classes = opt_div.get('class', [])
                                    if 'correct' in classes:
                                        correct_answer = letter

                                # Clean question text and options format check
                                if not question_text or len(options_dict) < 2:
                                    continue

                                # Normalize text to check duplicates
                                normalized = re.sub(r'[^\w\s]', '', question_text).lower().strip()
                                normalized = re.sub(r'\s+', ' ', normalized)
                                text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                                # Check duplicate
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
                                    safe_text = question_text[:50].encode('ascii', errors='replace').decode('ascii')
                                    self.stdout.write(f"    [DRY RUN] Would save: {safe_text}... | Answer: {correct_answer}")
                                
                                questions_imported += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  Error processing post questions: {e}"))
                        errors_count += 1
                    
                    posts_fetched += 1
                
                # Advance pagination
                start_index += page_size

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fetching page starting at {start_index}: {e}"))
                break

        self.stdout.write(self.style.SUCCESS(
            f"\nIngestion Complete!\n"
            f"  - Posts fetched: {posts_fetched}\n"
            f"  - Questions imported: {questions_imported}\n"
            f"  - Duplicates skipped: {duplicates_skipped}\n"
            f"  - Errors encountered: {errors_count}"
        ))
