from django.core.management.base import BaseCommand
from django.db.models import Q
from questionbank.models import Question, StudyFeedCard
from questionbank.kpsc_format import apply_to_question, is_servable, format_question_payload


class Command(BaseCommand):
    help = (
        "Normalize every MCQ to official Kerala PSC A-D format, "
        "unpublish shuffled/broken items, and rewrite study-feed cards."
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write changes to the database')
        parser.add_argument('--limit', type=int, default=0, help='Optional max questions to process')

    def handle(self, *args, **options):
        apply = options['apply']
        limit = options['limit']
        qs = Question.objects.all().order_by('id')
        if limit:
            qs = qs[:limit]

        stats = {
            'scanned': 0,
            'normalized': 0,
            'unpublished': 0,
            'republished': 0,
            'skipped_error': 0,
        }
        reason_counts = {}

        self.stdout.write(self.style.NOTICE(
            f"{'APPLYING' if apply else 'DRY RUN'} Kerala PSC option normalization"
        ))

        for q in qs.iterator(chunk_size=500):
            stats['scanned'] += 1
            original_opts = q.options
            original_text = q.text
            original_answer = q.correct_answer
            original_public = q.is_public

            try:
                issues = apply_to_question(q)
            except Exception as exc:
                stats['skipped_error'] += 1
                self.stderr.write(f"id={q.id} normalize failed: {exc}")
                continue

            changed = (
                q.options != original_opts
                or q.text != original_text
                or q.correct_answer != original_answer
            )
            should_serve = not issues
            if not should_serve:
                for issue in issues:
                    reason_counts[issue] = reason_counts.get(issue, 0) + 1

            if apply:
                try:
                    if changed:
                        q.save()
                        stats['normalized'] += 1
                    if should_serve and not original_public:
                        Question.objects.filter(pk=q.pk).update(is_public=True)
                        stats['republished'] += 1
                    elif (not should_serve) and original_public:
                        Question.objects.filter(pk=q.pk).update(is_public=False)
                        stats['unpublished'] += 1
                except Exception as exc:
                    stats['skipped_error'] += 1
                    self.stderr.write(f"id={q.id} save failed: {exc}")
            else:
                if changed:
                    stats['normalized'] += 1
                if should_serve and not original_public:
                    stats['republished'] += 1
                elif (not should_serve) and original_public:
                    stats['unpublished'] += 1

        feed_fixed = 0
        if apply:
            for card in StudyFeedCard.objects.filter(card_type='question').iterator():
                data = card.content_data if isinstance(card.content_data, dict) else {}
                qid = data.get('question_id')
                question = None
                if qid:
                    question = Question.objects.filter(pk=qid).first()
                if question and not is_servable(question.text, question.options, question.correct_answer):
                    card.delete()
                    feed_fixed += 1
                    continue
                source_text = question.text if question else (data.get('question_text') or data.get('text') or '')
                source_opts = question.options if question else data.get('options')
                source_ans = question.correct_answer if question else data.get('correct_answer')
                payload = format_question_payload(
                    source_text, source_opts, source_ans,
                    (question.explanation if question else data.get('explanation')) or '',
                    extra={'question_id': qid},
                )
                payload['question_text'] = payload['text']
                if payload != data:
                    card.content_data = payload
                    card.save(update_fields=['content_data'])
                    feed_fixed += 1

        self.stdout.write(self.style.SUCCESS("=== KPSC NORMALIZE RESULTS ==="))
        for key, val in stats.items():
            self.stdout.write(f"{key}: {val}")
        self.stdout.write("unpublished_reasons:")
        for key, val in sorted(reason_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {key}: {val}")
        if apply:
            self.stdout.write(f"study_feed_cards_rewritten: {feed_fixed}")
        else:
            self.stdout.write(self.style.WARNING("Re-run with --apply to write changes."))
