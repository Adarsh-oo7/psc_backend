import os
import time
from django.core.management.base import BaseCommand, CommandError
from questionbank.models import Question

class Command(BaseCommand):
    help = "Generates and caches AI explanations for approved questions using Groq"

    def add_arguments(self, parser):
        parser.add_argument('--batch', type=int, default=100, help="Number of questions to process")
        parser.add_argument('--topic', type=str, help="Filter questions by topic name")

    def handle(self, *args, **options):
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            raise CommandError("GROQ_API_KEY environment variable is not set.")

        try:
            from groq import Groq
            client = Groq(api_key=api_key)
        except ImportError:
            raise CommandError("groq is not installed. Please install it using: pip install groq")

        try:
            from tqdm import tqdm
        except ImportError:
            tqdm = None

        batch_size = options['batch']
        topic_name = options['topic']

        # Fetch questions
        queryset = Question.objects.filter(ai_explanation='', status='approved')
        if topic_name:
            queryset = queryset.filter(topic__name__iexact=topic_name)

        # Slice to batch size
        questions = list(queryset[:batch_size])
        total_questions = len(questions)

        if total_questions == 0:
            self.stdout.write(self.style.SUCCESS("No questions without AI explanations found. Done!"))
            return

        self.stdout.write(f"Generating explanations for {total_questions} questions...")

        generated_count = 0
        error_count = 0

        # Loop with progress bar if tqdm is installed
        iterable = tqdm(questions, total=total_questions) if tqdm else questions

        for q in iterable:
            opt_a = q.options.get('A', '')
            opt_b = q.options.get('B', '')
            opt_c = q.options.get('C', '')
            opt_d = q.options.get('D', '')
            correct_val = q.correct_answer
            correct_text = q.options.get(correct_val, '')

            prompt = f"""
Kerala PSC Question: {q.text}
Options: A) {opt_a}  B) {opt_b}  C) {opt_c}  D) {opt_d}
Correct Answer: {correct_val}

Explain WHY "{correct_text}" is the correct answer.
Write in simple English. Maximum 3 sentences.
Add one memory trick if possible.
Do not start with "The correct answer is" — start directly with the explanation.
Keep under 80 words total.
"""

            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                )
                explanation = chat_completion.choices[0].message.content.strip()
                q.ai_explanation = explanation
                q.save()
                generated_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"\nError generating explanation for question {q.id}: {e}"))
                error_count += 1

            # Sleep to satisfy rate limits (0.1 seconds)
            time.sleep(0.1)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Generated: {generated_count} explanations | ⏭️ Skipped: {error_count} errors"
        ))
