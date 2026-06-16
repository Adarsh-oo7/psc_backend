import re
import hashlib
from difflib import SequenceMatcher
from .models import Question

def normalize_text(text):
    if not text:
        return ""
    # Normalize text: lowercase, remove punctuation, strip
    normalized = re.sub(r'[^\w\s]', '', text).lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def find_similar_questions(new_question_text, threshold=0.85):
    normalized_new = normalize_text(new_question_text)
    if not normalized_new:
        return []
    
    # 1. Exact match check using hash
    new_hash = hashlib.sha256(normalized_new.encode('utf-8')).hexdigest()
    exact_match = Question.objects.filter(text_hash=new_hash)
    if exact_match.exists():
        return list(exact_match)
        
    # 2. Optimization: Retrieve questions sharing the same first word
    words = normalized_new.split()
    if not words:
        return []
    first_word = words[0]
    
    # We query candidate questions using database icontains
    candidates = Question.objects.filter(text__icontains=first_word)
    
    similar_questions = []
    for q in candidates:
        normalized_existing = normalize_text(q.text)
        existing_words = normalized_existing.split()
        if not existing_words or existing_words[0] != first_word:
            continue
            
        ratio = SequenceMatcher(None, normalized_new, normalized_existing).ratio()
        if ratio >= threshold:
            similar_questions.append((q, ratio))
            
    # Sort by ratio descending
    similar_questions.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in similar_questions]
