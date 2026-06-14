import os
import requests
from django.conf import settings
from .models import AIExplanationCache, Question

def get_ai_explanation(question, language='en'):
    """
    Retrieves or generates an explanation for a question in English or Malayalam.
    Uses local cache (AIExplanationCache) first.
    If miss, calls Gemini API (or returns mock if key is missing).
    """
    # 1. Check Cache
    cached = AIExplanationCache.objects.filter(question=question, language=language).first()
    if cached:
        return cached.explanation_text

    # 2. Get API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    
    explanation_text = ""
    if api_key:
        try:
            # Construct Prompt
            options_str = "\n".join([f"{k}: {v}" for k, v in question.options.items()]) if isinstance(question.options, dict) else str(question.options)
            
            if language == 'ml':
                prompt = (
                    f"Explain the following Kerala PSC exam question in detail in Malayalam. Explain why the correct option is the right answer and why others are wrong.\n"
                    f"Question: {question.text}\n"
                    f"Options:\n{options_str}\n"
                    f"Correct Answer: {question.correct_answer}\n"
                    f"Provide the explanation in clear, simple Malayalam language (മലയാളത്തിൽ) with English terms in brackets if necessary."
                )
            else:
                prompt = (
                    f"Explain the following Kerala PSC exam question in detail in English. Explain why the correct option is the right answer and why others are wrong.\n"
                    f"Question: {question.text}\n"
                    f"Options:\n{options_str}\n"
                    f"Correct Answer: {question.correct_answer}\n"
                )

            # Call Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                explanation_text = data['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            # Fall back to mock on failure
            explanation_text = f"Failed to fetch AI explanation: {str(e)}"

    # If no api key or API call failed/skipped, return a high-quality mock explanation
    if not explanation_text or explanation_text.startswith("Failed to fetch"):
        correct_opt_text = question.options.get(question.correct_answer, question.correct_answer) if isinstance(question.options, dict) else question.correct_answer
        if language == 'ml':
            explanation_text = (
                f"ശരിയായ ഉത്തരം: {question.correct_answer}) {correct_opt_text}\n\n"
                f"വിശദീകരണം: ഈ ചോദ്യം കേരള പി.എസ്.സി പരീക്ഷകളിൽ ആവർത്തിച്ചു ചോദിക്കുന്ന ഒന്നാണ്. "
                f"തന്നിരിക്കുന്ന ചോദ്യത്തിൽ ശരിയായ ഉത്തരം {question.correct_answer} ആണ്. "
                f"മറ്റു ഓപ്ഷനുകൾ തെറ്റായ വിവരങ്ങളാണ് നൽകുന്നത്."
            )
        else:
            explanation_text = (
                f"Correct Answer: {question.correct_answer}) {correct_opt_text}\n\n"
                f"Explanation: For the question '{question.text}', the correct answer is option {question.correct_answer}. "
                f"The option '{correct_opt_text}' accurately represents the facts requested. "
                f"Other options are factually incorrect or inappropriate contextually."
            )

    # 3. Save to Cache
    try:
        AIExplanationCache.objects.create(
            question=question,
            language=language,
            explanation_text=explanation_text
        )
    except Exception:
        # Ignore unique constraint issues if race condition occurred
        pass

    return explanation_text
