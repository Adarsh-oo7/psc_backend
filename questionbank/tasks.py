import os
import time
from celery import shared_task
from .models import Question

@shared_task
def generate_explanations_nightly():
    """
    Nightly Celery task to generate Groq AI explanations
    for approved questions lacking them.
    """
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return "GROQ_API_KEY environment variable is not set."

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
    except ImportError:
        return "groq package is not installed."

    # Process a batch of up to 200 questions without explanations
    questions = Question.objects.filter(ai_explanation='', status='approved')[:200]
    count = 0
    errors = 0

    for q in questions:
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
            count += 1
        except Exception:
            errors += 1

        # Rate limit spacing (0.1 seconds)
        time.sleep(0.1)

    return f"Nightly task complete: Generated {count} explanations, {errors} errors."
