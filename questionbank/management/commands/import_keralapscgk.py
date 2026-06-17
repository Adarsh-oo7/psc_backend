import re
import hashlib
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from questionbank.models import Question, Topic, Exam, ExamCategory


def extract_options_and_answer(q_text, ans_text):
    patterns = [
        r'\[1\]\s*(.+?)\s*\[2\]\s*(.+?)\s*\[3\]\s*(.+?)\s*\[4\]\s*(.+?)(?:\s*\[5\]\s*(.+?))?\s*$',
        r'\[a\]\s*(.+?)\s*\[b\]\s*(.+?)\s*\[c\]\s*(.+?)\s*\[d\]\s*(.+?)(?:\s*\[e\]\s*(.+?))?\s*$',
        r'\([1]\)\s*(.+?)\s*\([2]\)\s*(.+?)\s*\([3]\)\s*(.+?)\s*\([4]\)\s*(.+?)(?:\s*\([5]\)\s*(.+?))?\s*$',
        r'\([aA]\)\s*(.+?)\s*\([bB]\)\s*(.+?)\s*\([cC]\)\s*(.+?)\s*\([dD]\)\s*(.+?)(?:\s*\([eE]\)\s*(.+?))?\s*$',
        r'1\)\s*(.+?)\s*2\)\s*(.+?)\s*3\)\s*(.+?)\s*4\)\s*(.+?)(?:\s*5\)\s*(.+?))?\s*$',
        r'[aA]\)\s*(.+?)\s*[bB]\)\s*(.+?)\s*[cC]\)\s*(.+?)\s*[dD]\)\s*(.+?)(?:\s*[eE]\)\s*(.+?))?\s*$',
        r'1\.\s*(.+?)\s*2\.\s*(.+?)\s*3\.\s*(.+?)\s*4\.\s*(.+?)(?:\s*5\.\s*(.+?))?\s*$',
        r'\b[aA]\.\s*(.+?)\s*\b[bB]\.\s*(.+?)\s*\b[cC]\.\s*(.+?)\s*\b[dD]\.\s*(.+?)(?:\s*\b[eE]\.\s*(.+?))?\s*$',
    ]
    
    clean_q = q_text
    options = {}
    correct_letter = 'A'
    
    found_pattern = False
    opt_list = []
    
    for pat in patterns:
        m = re.search(pat, q_text, re.IGNORECASE | re.DOTALL)
        if m:
            opt_list = [m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4).strip()]
            clean_q = q_text[:m.start()].strip()
            # Remove trailing dash/colon/spaces
            clean_q = re.sub(r'[:\-–\s]+$', '', clean_q).strip()
            found_pattern = True
            break
            
    if found_pattern:
        options = {
            'A': opt_list[0],
            'B': opt_list[1],
            'C': opt_list[2],
            'D': opt_list[3]
        }
        
        ans_clean = ans_text.lower().strip()
        ans_clean = re.sub(r'^(ans\.|answer|ഉത്തരം)\s*[:\-–]?\s*', '', ans_clean).strip()
        
        # Check bracketed/parenthesized option index first
        m_index = re.search(r'^[\(\[]([1-5a-e])[\)\]]', ans_clean)
        if not m_index:
            # Check bare option letter or number followed by boundary
            m_index = re.search(r'^([1-5a-e])\b', ans_clean)
            
        if m_index:
            key = m_index.group(1)
            if key in ('1', '2', '3', '4', '5'):
                idx = int(key) - 1
                if idx < 4:
                    correct_letter = ['A', 'B', 'C', 'D'][idx]
                else:
                    correct_letter = 'D'
            else:
                letter = key.upper()
                if letter in ('A', 'B', 'C', 'D'):
                    correct_letter = letter
                else:
                    correct_letter = 'D'
        else:
            # Substring matching
            for letter, opt_val in options.items():
                opt_clean = opt_val.lower().strip()
                if opt_clean and (opt_clean in ans_clean or ans_clean in opt_clean):
                    correct_letter = letter
                    break
    else:
        short_correct = ans_text[:50]
        options = {
            'A': ans_text,
            'B': f'Not {short_correct}' if len(ans_text) > 2 else 'Option B',
            'C': 'None of the above',
            'D': 'All of the above',
        }
        correct_letter = 'A'
        
    return clean_q, options, correct_letter


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
                    santosh_inputs = soup.find_all('input', class_=re.compile(r'^santh?osh$'))

                    # Format C: quiz_container divs (no buttons, question + bold answer in .single.enabled)
                    quiz_container_divs = soup.find_all('div', class_='single') if not mcq_containers and not santosh_inputs else []

                    # Format D: Inline numbered Q with bold answer ("1. Question - <b>Answer</b>")
                    has_format_d = False
                    if not mcq_containers and not santosh_inputs and not quiz_container_divs:
                        # Heuristic: numbered list with <b> tags in same paragraph/block after dash
                        bold_tags = soup.find_all('b')
                        text_nodes_with_dash = re.findall(r'\d+\.\s*.+?\s+-\s+<b>(.+?)</b>', html_content)
                        has_format_d = len(text_nodes_with_dash) >= 3

                    if not mcq_containers and not santosh_inputs and not quiz_container_divs and not has_format_d:
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
                    # Supports multiple onclick variants:
                    #   B1: value=('Answer - X')          → classic format
                    #   B2: value=('Answer: [d] ')         → Maths MCQ format (letter option)
                    #   B3: value=("answer text")          → direct value (Malayalam/Kerala)
                    # ================================================
                    elif santosh_inputs:
                        self.stdout.write(f"  [Format B - Q&A] Found {len(santosh_inputs)} items.")

                        def extract_answer_from_onclick(onclick_str, btn_value=''):
                            """Try all known onclick formats and return the answer text, or None."""
                            # Skip 'Solution' toggle buttons
                            if btn_value and btn_value.strip().lower() in ('solution', 'hide solution'):
                                return None
                            if 'getElementsByTagName' in onclick_str:
                                return None

                            # B1: Answer - X  (classic: dash separator)
                            m = re.search(r'Answer\s*[-\u2013]\s*(.+?)["\')]', onclick_str)
                            if m:
                                return m.group(1).strip()

                            # B2: Answer: [d] X  (Maths: colon + letter in brackets)
                            m = re.search(r'Answer:\s*\[([a-dA-D])\]\s*(.*?)["\')]', onclick_str)
                            if m:
                                letter = m.group(1).upper()  # keep A-D letter as answer
                                extra = m.group(2).strip()
                                return f'[{letter}] {extra}'.strip() if extra else f'[{letter}]'

                            # B2b: Answer: [d] with no trailing text
                            m = re.search(r'Answer:\s*\[([a-dA-D])\s*\]', onclick_str)
                            if m:
                                return f'[{m.group(1).upper()}]'

                            # B3: value=("direct text") or value=('direct text')  — no Answer prefix
                            # Only apply if button value is something like 'Answer' or Malayalam 'ഉത്തരം'
                            btn_val_lower = (btn_value or '').strip().lower()
                            if btn_val_lower in ('answer', '\u0d09\u0d24\u0d4d\u0d24\u0d30\u0d02', '\u0d09\u0d24\u0d4d\u0d24\u0d30'):
                                m = re.search(r'value\s*=\s*[\(\[]\s*["\'](.+?)["\']', onclick_str)
                                if m:
                                    txt = m.group(1).strip()
                                    # Reject if it's just whitespace or looks like code
                                    if txt and len(txt) >= 1 and 'getElementsByTagName' not in txt:
                                        return txt

                            return None

                        # Detect structural divs containing santosh buttons
                        containers = soup.find_all(class_='single')
                        if not containers:
                            containers = soup.find_all(class_='single-question-container')
                        if not containers:
                            containers = soup.find_all(class_='quiz-container')

                        structural_blocks = []
                        if containers:
                            for container in containers:
                                if container.find('input', class_=re.compile(r'^santh?osh$')):
                                    structural_blocks.append(container)

                        if len(structural_blocks) >= 3:
                            blocks_soup = structural_blocks
                            self.stdout.write(f"  Using {len(blocks_soup)} structural Q&A containers as blocks.")
                        else:
                            # Fallback: Split HTML by <hr> tags to get individual Q&A blocks
                            blocks = re.split(r'<hr\s*/?>', html_content, flags=re.IGNORECASE)
                            blocks_soup = [BeautifulSoup(b, 'html.parser') for b in blocks]

                        for block_soup in blocks_soup:
                            # Find the FIRST non-Solution santosh button in this block
                            all_btns = block_soup.find_all('input', class_=re.compile(r'^santh?osh$'))
                            btn = None
                            correct_text = None
                            for candidate_btn in all_btns:
                                onclick = candidate_btn.get('onclick', '')
                                val = candidate_btn.get('value', '')
                                answer = extract_answer_from_onclick(onclick, val)
                                if answer is not None:
                                    btn = candidate_btn
                                    correct_text = answer
                                    break

                            if btn is None or not correct_text:
                                continue

                            # Remove ALL buttons from block_soup to get clean question text
                            for b in block_soup.find_all('input', class_=re.compile(r'^santh?osh$')):
                                b.decompose()

                            # Decompose any questionNum divs
                            num_div = block_soup.find(class_='questionNum')
                            if num_div:
                                num_div.decompose()

                            raw_text = block_soup.get_text(separator=' ', strip=True)
                            question_text = re.sub(r'^\d+[\s\.\)]+', '', raw_text).strip()
                            question_text = re.sub(r'\s+', ' ', question_text).strip()
                            question_text = re.sub(r'[:\-–\s]+$', '', question_text).strip() # clean trailing dash/colon

                            if not question_text or len(question_text) < 8:
                                continue

                            # Extract options and clean answer using the helper function
                            clean_q, options_dict, correct_answer = extract_options_and_answer(question_text, correct_text)

                            parsed_questions.append({
                                'text': clean_q,
                                'options': options_dict,
                                'correct_answer': correct_answer,
                            })

                    # ================================================
                    # FORMAT C: quiz_container divs (question + bold answer)
                    # Structure: <div class="single enabled"><div class="questionNum">N</div>Q text<br><b>Answer</b></div>
                    # ================================================
                    elif quiz_container_divs:
                        self.stdout.write(f"  [Format C - quiz_container] Found {len(quiz_container_divs)} items.")
                        for container in quiz_container_divs:
                            # Remove question number div
                            num_div = container.find(class_='questionNum')
                            if num_div:
                                num_div.decompose()

                            # Extract bold answer
                            bold = container.find('b')
                            correct_text = bold.get_text(strip=True) if bold else None
                            if bold:
                                bold.decompose()

                            if not correct_text:
                                continue

                            question_text = container.get_text(separator=' ', strip=True)
                            question_text = re.sub(r'^\d+[\s\.\)]+', '', question_text).strip()
                            question_text = re.sub(r'\s+', ' ', question_text).strip()
                            question_text = re.sub(r'[:\-–\s]+$', '', question_text).strip() # clean trailing dash/colon

                            if not question_text or len(question_text) < 8:
                                continue

                            # Extract options and clean answer using the helper function
                            clean_q, options_dict, correct_answer = extract_options_and_answer(question_text, correct_text)

                            parsed_questions.append({
                                'text': clean_q,
                                'options': options_dict,
                                'correct_answer': correct_answer,
                            })

                    # ================================================
                    # FORMAT D: Inline Q - <b>Answer</b> pattern
                    # Structure: "1. Question text - <b>Answer</b><br/>" repeated
                    # ================================================
                    elif has_format_d:
                        self.stdout.write(f"  [Format D - inline bold] Parsing Q-Answer pairs.")
                        # Split HTML content by br, p, and div tags to get individual Q-A lines
                        lines = re.split(r'<br\s*/?>|</?p>|</div>', html_content, flags=re.IGNORECASE)
                        qa_pattern = re.compile(
                            r'(?:\d+[\s\.\)]+)?(.+?)\s*[:\-–]\s*<b>([^<]+)</b>',
                            re.IGNORECASE | re.DOTALL
                        )
                        for line in lines:
                            m = qa_pattern.search(line)
                            if m:
                                q_raw = m.group(1).strip()
                                a_raw = m.group(2).strip()

                                # Clean HTML from Q & A
                                q_soup = BeautifulSoup(q_raw, 'html.parser')
                                q_text = q_soup.get_text(separator=' ', strip=True)

                                a_soup = BeautifulSoup(a_raw, 'html.parser')
                                correct_text = a_soup.get_text(separator=' ', strip=True)

                                # Clean leading numbers and trailing punctuation
                                q_text = re.sub(r'^\d+[\s\.\)]+', '', q_text).strip()
                                q_text = re.sub(r'[:\-–\s]+$', '', q_text).strip()

                                # Ignore lines that are actually header templates
                                if 'http' in q_text or 'style=' in q_text or len(q_text) < 5:
                                    continue

                                # Extract options and clean answer using the helper function
                                clean_q, options_dict, correct_answer = extract_options_and_answer(q_text, correct_text)

                                parsed_questions.append({
                                    'text': clean_q,
                                    'options': options_dict,
                                    'correct_answer': correct_answer,
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
                                if options_dict and isinstance(options_dict, dict):
                                    opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options_dict.items()))
                                    normalized = f"{normalized}||{opts_str}"
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
