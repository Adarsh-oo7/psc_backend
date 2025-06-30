import json
import re
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect

# --- Import all necessary models and the form ---
from .models import (
    ExamCategory, Exam, Topic, Question, 
    UserAnswer, Bookmark, Report, UserProfile, ExamSyllabus
)
from .forms import BulkQuestionUploadForm

# ===================================================================
# --- Model Admin Configurations ---
# ===================================================================

@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'category', 'duration_minutes')
    list_filter = ('category', 'year')
    search_fields = ('name',)

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'institute')
    list_filter = ('institute',)
    search_fields = ('name',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'exam', 'topic', 'difficulty', 'institute')
    list_filter = ('exam', 'topic', 'difficulty', 'institute')
    search_fields = ('text',)
    
    # --- This adds the custom URL for our bulk upload page ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), name='questionbank_question_bulk_upload'),
        ]
        return custom_urls + urls

    # --- This is the view that handles the logic for the bulk upload page ---
    def bulk_upload_view(self, request):
        if request.method == 'POST':
            form = BulkQuestionUploadForm(request.POST)
            if form.is_valid():
                exam = form.cleaned_data['exam']
                topic = form.cleaned_data['topic']
                questions_text = form.cleaned_data['questions_text']
                
                # Split the text into blocks based on the question number pattern
                # Updated regex to match **1. format
                question_blocks = re.split(r'\n(?=\*\*\d+\.)', questions_text)
                saved_count = 0
                error_count = 0

                for block in question_blocks:
                    block = block.strip()
                    if not block:
                        continue
                    try:
                        # Updated regex patterns to match the actual format
                        
                        # Extract question text - from **1. to ```json
                        text_match = re.search(r'^\*\*\d+\.\s*(.*?)\*\*\s*```json', block, re.DOTALL)
                        if not text_match:
                            raise ValueError("Could not find question text")
                        text = text_match.group(1).strip()
                        
                        # Extract options JSON
                        options_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', block)
                        if not options_match:
                            raise ValueError("Could not find options JSON")
                        options_str = options_match.group(1)
                        options = json.loads(options_str)
                        
                        # Extract answer - **Answer: C**
                        answer_match = re.search(r'\*\*Answer:\s*([A-D])\*\*', block)
                        if not answer_match:
                            raise ValueError("Could not find answer")
                        answer = answer_match.group(1).strip().upper()
                        
                        # Extract difficulty - **Difficulty: Medium**
                        difficulty_match = re.search(r'\*\*Difficulty:\s*(.*?)\*\*', block)
                        if not difficulty_match:
                            raise ValueError("Could not find difficulty")
                        difficulty = difficulty_match.group(1).strip().lower()
                        
                        # Extract explanation - *Explanation: ...*
                        explanation_match = re.search(r'\*Explanation:\s*(.*?)\*', block, re.DOTALL)
                        explanation = explanation_match.group(1).strip() if explanation_match else ''

                        # Create the Question object in the database
                        Question.objects.create(
                            exam=exam, 
                            topic=topic, 
                            text=text, 
                            options=options,
                            correct_answer=answer, 
                            explanation=explanation,
                            difficulty=difficulty, 
                            institute=None  # Global questions
                        )
                        saved_count += 1
                        
                    except (AttributeError, ValueError, json.JSONDecodeError) as e:
                        error_count += 1
                        # Show more detailed error information
                        messages.error(request, f"Could not parse question block. Error: {str(e)}. Block preview: '{block[:100]}...'")

                if saved_count > 0:
                    self.message_user(request, f"Successfully saved {saved_count} new questions.", messages.SUCCESS)
                if error_count > 0:
                    self.message_user(request, f"Failed to parse and save {error_count} questions.", messages.WARNING)
                
                return redirect('..')  # Redirect back to the main Question list page
        else:
            form = BulkQuestionUploadForm()

        context = self.admin_site.each_context(request)
        context['form'] = form
        context['title'] = "Bulk Upload Questions"
        return render(request, 'admin/questionbank/question/bulk_upload.html', context)

@admin.register(ExamSyllabus)
class ExamSyllabusAdmin(admin.ModelAdmin):
    list_display = ('exam', 'topic', 'num_questions')
    list_filter = ('exam',)

# Also register other important models to make them visible in the admin
admin.site.register(UserProfile)
admin.site.register(Bookmark)
admin.site.register(Report)
admin.site.register(UserAnswer)