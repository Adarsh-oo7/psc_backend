from django.core.management.base import BaseCommand
from questionbank.models import Question
from questionbank.utils import normalize_text
from difflib import SequenceMatcher

class Command(BaseCommand):
    help = "Find fuzzy duplicate questions and optionally reject the lower quality ones."

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically mark lower quality duplicates as rejected'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.85,
            help='Similarity threshold (default 0.85)'
        )

    def handle(self, *args, **options):
        fix = options['fix']
        threshold = options['threshold']

        self.stdout.write("Fetching all active/approved/pending questions...")
        # Only compare questions that are not already rejected
        questions = list(Question.objects.exclude(status='rejected'))
        self.stdout.write(f"Loaded {len(questions)} questions.")

        # Group by first word
        by_first_word = {}
        for q in questions:
            norm = normalize_text(q.text)
            words = norm.split()
            if not words:
                continue
            first_word = words[0]
            by_first_word.setdefault(first_word, []).append((q, norm))

        # Find duplicates
        duplicate_groups = []
        seen_ids = set()

        for first_word, items in by_first_word.items():
            if len(items) < 2:
                continue
            
            # If the group is huge, warn and skip to prevent performance issues
            if len(items) > 300:
                self.stdout.write(self.style.WARNING(f"Large group for word '{first_word}': {len(items)} questions. Skipping to prevent performance issues."))
                continue

            # Compare pairs
            n = len(items)
            for i in range(n):
                q1, norm1 = items[i]
                if q1.id in seen_ids:
                    continue
                
                group = [q1]
                for j in range(i + 1, n):
                    q2, norm2 = items[j]
                    if q2.id in seen_ids:
                        continue
                    
                    ratio = SequenceMatcher(None, norm1, norm2).ratio()
                    if ratio >= threshold:
                        group.append(q2)
                        seen_ids.add(q2.id)

                if len(group) > 1:
                    seen_ids.add(q1.id)
                    duplicate_groups.append(group)

        self.stdout.write(self.style.SUCCESS(f"Found {len(duplicate_groups)} groups of duplicates."))

        def get_quality_score(q):
            score = 0
            if q.verified or q.is_verified:
                score += 10
            if q.explanation:
                score += 5
            if q.ai_explanation:
                score += 5
            if q.times_appeared > 1:
                score += 2
            if q.status == 'approved':
                score += 1
            score += q.exams.count()
            return score

        for group in duplicate_groups:
            self.stdout.write(f"\nDuplicate Group ({len(group)} questions):")
            # Sort group by quality score descending, then by ID ascending
            group.sort(key=lambda x: (-get_quality_score(x), x.id))
            best = group[0]
            self.stdout.write(self.style.SUCCESS(f"  [KEEP] ID {best.id} (Score {get_quality_score(best)}): {best.text[:80]}..."))
            
            for other in group[1:]:
                self.stdout.write(self.style.WARNING(f"  [REJECT] ID {other.id} (Score {get_quality_score(other)}): {other.text[:80]}..."))
                if fix:
                    other.status = 'rejected'
                    other.save()
                    self.stdout.write(f"    -> Rejected ID {other.id}")
