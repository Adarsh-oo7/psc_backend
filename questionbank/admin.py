import json
import re
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.utils.html import format_html

# --- Import all necessary models and the form ---
from .models import (
    ExamCategory, Exam, Topic, Question, 
    UserAnswer, Bookmark, Report, UserProfile, ExamSyllabus
)
from .forms import BulkQuestionUploadForm


#===================================================================
#--- Model Admin Configurations ---
#===================================================================


@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    search_fields = ('name',)

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



    
import re
import json
import traceback
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'display_exams', 'topic', 'sub_topic', 'difficulty')
    list_filter = ('exams', 'topic', 'difficulty', 'institute')
    search_fields = ('text',)
    filter_horizontal = ('exams',)

    fieldsets = (
        ('Core Details', {'fields': ('text', 'topic', 'sub_topic')}),
        ('Question Content', {
            'fields': ('options', 'correct_answer', 'explanation'),
            'description': """<p style="font-size: 1.1em;"><strong>Options Format:</strong> Please enter the options as a valid JSON object.</p><p>Example:</p><pre><code>{\n  "A": "Option text 1",\n  "B": "Option text 2",\n  "C": "Option text 3",\n  "D": "Option text 4"\n}</code></pre>"""
        }),
        ('Categorization & Difficulty', {'fields': ('difficulty', 'exams', 'institute')}),
    )

    def display_exams(self, obj):
        return ", ".join([exam.name for exam in obj.exams.all()])
    display_exams.short_description = 'Exams'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), name='questionbank_question_bulk_upload')]
        return custom_urls + urls

    def bulk_upload_view(self, request):
        if request.method == 'POST':
            form = BulkQuestionUploadForm(request.POST)
            if form.is_valid():
                questions_text = form.cleaned_data['questions_text']
                
                # Updated regex pattern to handle your format
                pattern = re.compile(
                    r'\*?\*?(\d+)\.\s+(.*?)\s*'  # Question number and text
                    r'```json\s*(\{.*?\})\s*```\s*'  # JSON options
                    r'\*?\*?Answer:\s*([A-D])\*?\*?\s*'  # Answer
                    r'(?:\*?Explanation:\s*(.*?)\s*)?'  # Optional explanation
                    r'\*?\*?Difficulty:\s*(.*?)\*?\*?\s*'  # Difficulty
                    r'\*?\*?Category:\s*(.*?)\s*\|\s*Suitable for:\s*(.*?)(?=\n\n|\*\*\d+\.|\Z)',  # Category and suitable for
                    re.MULTILINE | re.DOTALL
                )
                
                saved_count, error_count, skipped_count = 0, 0, 0
                
                print(f"Input text length: {len(questions_text)}")  # Debug
                print(f"First 500 chars: {questions_text[:500]}")  # Debug

                matches = list(pattern.finditer(questions_text))
                print(f"Found {len(matches)} matches")  # Debug

                for i, match in enumerate(matches):
                    print(f"Match groups: {match.groups()}")
                    for j, group in enumerate(match.groups()):
                        print(f"Group {j}: {repr(group)}")
                    try:
                        question_num = match.group(1)
                        # Clean up question text - remove extra asterisks
                        text = match.group(2).strip().rstrip('*').strip()
                        options_json = match.group(3)
                        answer = match.group(4).strip().upper()
                        # Clean up explanation - remove leading/trailing asterisks
                        explanation = match.group(5).strip().strip('*').strip() if match.group(5) else ""
                        difficulty = match.group(6).strip().lower()
                        category_info = match.group(7).strip()
                        # Clean up suitable_for - remove extra asterisks and carriage returns
                        suitable_for = match.group(8).strip().rstrip('*').replace('\r', '').replace('\n', '').strip()
                        
                        print(f"Processing question {question_num}: {text[:50]}...")  # Debug
                        print(f"Cleaned suitable_for: '{suitable_for}'")  # Debug
                        
                        # Check for duplicates
                        if Question.objects.filter(text__iexact=text).exists():
                            print(f"Skipping duplicate: {text[:50]}")  # Debug
                            skipped_count += 1
                            continue
                        
                        # Parse category (take the part before |)
                        category_name = category_info.split('|')[0].strip()
                        if not category_name:
                            raise ValueError("Category cannot be empty")
                        
                        # Get or create topic
                        topic, created = Topic.objects.get_or_create(
                            name__iexact=category_name,
                            defaults={'name': category_name}
                        )
                        if created:
                            print(f"Created new topic: {category_name}")
                        
                        # Parse options JSON
                        try:
                            options = json.loads(options_json)
                        except json.JSONDecodeError as e:
                            raise ValueError(f"Invalid JSON format in options: {e}")
                        
                        # Handle exams - clean up the suitable_for string
                        if not suitable_for:
                            suitable_for = "General"
                        
                        exam_names = [name.strip() for name in suitable_for.split(',')]
                        
                        if "all psc exams" in suitable_for.lower():
                            exams_qs = Exam.objects.all()
                        else:
                            # Try to find exams by name (case-insensitive)
                            exams_qs = Exam.objects.filter(name__iregex=r'(' + '|'.join(exam_names) + ')')
                        
                        if not exams_qs.exists():
                            print(f"Warning: No exams found for: {suitable_for}")
                            # Create a default exam if none found
                            default_exam, _ = Exam.objects.get_or_create(
                                name="General",
                                defaults={'name': "General", 'year': 2024}
                            )
                            exams_qs = Exam.objects.filter(id=default_exam.id)
                        
                        # Validate difficulty
                        valid_difficulties = ['easy', 'medium', 'hard']
                        if difficulty not in valid_difficulties:
                            print(f"Warning: Invalid difficulty '{difficulty}', defaulting to 'medium'")
                            difficulty = 'medium'
                        
                        # Create question
                        question = Question.objects.create(
                            text=text,
                            topic=topic,
                            sub_topic=category_name,
                            options=options,
                            correct_answer=answer,
                            explanation=explanation,
                            difficulty=difficulty,
                        )
                        
                        # Set exams
                        question.exams.set(exams_qs)
                        saved_count += 1
                        print(f"Successfully saved question {question_num}")  # Debug
                        
                    except Exception as e:
                        error_count += 1
                        error_msg = f"Error processing question {i+1}: {str(e)}"
                        print(error_msg)  # Debug
                        print(f"Full traceback: {traceback.format_exc()}")  # Add full traceback for debugging
                        messages.error(request, error_msg)

                # Show results
                if saved_count > 0:
                    self.message_user(request, f"Successfully saved {saved_count} new questions.", messages.SUCCESS)
                if skipped_count > 0:
                    self.message_user(request, f"Skipped {skipped_count} questions that already exist.", messages.INFO)
                if error_count > 0:
                    self.message_user(request, f"Failed to parse {error_count} questions.", messages.WARNING)
                
                return redirect('..')
        else:
            form = BulkQuestionUploadForm()

        context = self.admin_site.each_context(request)
        context['form'] = form
        context['title'] = "Bulk Upload Questions"
        context['help_text'] = """
        <h3>Expected Format:</h3>
        <pre>
**1. Question text here?**
```json
{
  "A": "Option A text",
  "B": "Option B text", 
  "C": "Option C text",
  "D": "Option D text"
}
```
**Answer: A**
*Explanation: Your explanation here*
**Difficulty: Easy**
**Category: Your Category | Suitable for: HSST Computer Science**

**2. Next question...**
        </pre>
        """
        return render(request, 'admin/questionbank/question/bulk_upload.html', context)
    


@admin.register(ExamSyllabus)
class ExamSyllabusAdmin(admin.ModelAdmin):
    list_display = ('exam', 'topic', 'num_questions')
    list_filter = ('exam',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'institute', 'place')
    search_fields = ('user__username', 'institute__name')

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question_text', 'is_correct', 'answered_at')
    list_filter = ('is_correct', 'answered_at')
    search_fields = ('user__username', 'question__text')
    
    @admin.display(description='Question Text')
    def question_text(self, obj):
        return obj.question.text[:50]


# Register the remaining simple models.
admin.site.register(Bookmark)
admin.site.register(Report)