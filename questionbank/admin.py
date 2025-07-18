import json
import re
import traceback
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
                
                # Enhanced PSC-specific exam mapping with exact names
                psc_exam_mapping = {
                    # Driver related
                    'driver': 'Driver (Light / Heavy) (2025)',
                    'driver (light / heavy)': 'Driver (Light / Heavy) (2025)',
                    'driver (light/heavy)': 'Driver (Light / Heavy) (2025)',
                    'driver (light / heavy) (2025)': 'Driver (Light / Heavy) (2025)',
                    'driver (ldv / hdv)': 'Driver (LDV / HDV) (1000)',
                    'driver (ldv/hdv)': 'Driver (LDV / HDV) (1000)',
                    'ldv': 'Driver (LDV / HDV) (1000)',
                    'hdv': 'Driver (LDV / HDV) (1000)',
                    'light vehicle driver': 'Driver (Light / Heavy) (2025)',
                    'heavy vehicle driver': 'Driver (Light / Heavy) (2025)',
                    
                    # Police related
                    'police constable': 'Police Constable (2025)',
                    'police constable (2025)': 'Police Constable (2025)',
                    'civil police officer': 'Civil Police Officer (CPO) (2025)',
                    'civil police officer (cpo)': 'Civil Police Officer (CPO) (2025)',
                    'cpo': 'Civil Police Officer (CPO) (2025)',
                    'sub inspector': 'Sub Inspector of Police (SI) (2025)',
                    'sub inspector of police': 'Sub Inspector of Police (SI) (2025)',
                    'si': 'Sub Inspector of Police (SI) (2025)',
                    'si (2025)': 'Sub Inspector of Police (SI) (2025)',
                    'police si': 'Sub Inspector of Police (SI) (2025)',
                    'police sub inspector': 'Sub Inspector of Police (SI) (2025)',
                    
                    # Fire service
                    'fireman': 'Fireman (2025)',
                    'fireman (2025)': 'Fireman (2025)',
                    'fire service': 'Fireman (2025)',
                    
                    # Clerical positions
                    'last grade servant': 'Last Grade Servant (LGS) (2025)',
                    'lgs': 'Last Grade Servant (LGS) (2025)',
                    'lgs (2025)': 'Last Grade Servant (LGS) (2025)',
                    'peon': 'Peon / Attender (2025)',
                    'attender': 'Peon / Attender (2025)',
                    'peon / attender': 'Peon / Attender (2025)',
                    'peon/attender': 'Peon / Attender (2025)',
                    'typist': 'Typist / Clerk Typist (2025)',
                    'clerk typist': 'Typist / Clerk Typist (2025)',
                    'typist / clerk typist': 'Typist / Clerk Typist (2025)',
                    'ld clerk': 'LD Clerk (LDC) (2025)',
                    'ldc': 'LD Clerk (LDC) (2025)',
                    'ld clerk (ldc)': 'LD Clerk (LDC) (2025)',
                    'lower division clerk': 'LD Clerk (LDC) (2025)',
                    
                    # Assistant positions
                    'assistant': 'Assistant / Junior Assistant (Various Depts.) (2025)',
                    'junior assistant': 'Assistant / Junior Assistant (Various Depts.) (2025)',
                    'assistant / junior assistant': 'Assistant / Junior Assistant (Various Depts.) (2025)',
                    'secretariat assistant': 'Secretariat Assistant / Auditor (2025)',
                    'auditor': 'Secretariat Assistant / Auditor (2025)',
                    'secretariat assistant / auditor': 'Secretariat Assistant / Auditor (2025)',
                    'university assistant': 'University Assistant (2025)',
                    'assistant grade ii': 'Assistant Grade II (2025)',
                    'grade ii': 'Assistant Grade II (2025)',
                    'assistant grade 2': 'Assistant Grade II (2025)',
                    
                    # Specialized positions
                    'sales assistant': 'Sales Assistant (Bevco) (2025)',
                    'sales assistant (bevco)': 'Sales Assistant (Bevco) (2025)',
                    'bevco': 'Sales Assistant (Bevco) (2025)',
                    'civil excise officer': 'Civil Excise Officer (2025)',
                    'excise inspector': 'Excise Inspector (2025)',
                    'excise officer': 'Civil Excise Officer (2025)',
                    'beat forest officer': 'Beat Forest Officer (2025)',
                    'forest officer': 'Beat Forest Officer (2025)',
                    'assistant prison officer': 'Assistant Prison Officer (2025)',
                    'prison officer': 'Assistant Prison Officer (2025)',
                    'jailer': 'Assistant Prison Officer (2025)',
                    
                    # Engineering
                    'assistant engineer': 'Assistant Engineer (Civil, Mechanical, Electrical) (2025)',
                    'assistant engineer (civil, mechanical, electrical)': 'Assistant Engineer (Civil, Mechanical, Electrical) (2025)',
                    'ae': 'Assistant Engineer (Civil, Mechanical, Electrical) (2025)',
                    'civil engineer': 'Assistant Engineer (Civil, Mechanical, Electrical) (2025)',
                    'mechanical engineer': 'Assistant Engineer (Civil, Mechanical, Electrical) (2025)',
                    'electrical engineer': 'Assistant Engineer (Civil, Mechanical, Electrical) (2025)',
                    
                    # Health services
                    'junior health inspector': 'Junior Health Inspector (2025)',
                    'health inspector': 'Junior Health Inspector (2025)',
                    'jhi': 'Junior Health Inspector (2025)',
                    'staff nurse': 'Staff Nurse (2025)',
                    'nurse': 'Staff Nurse (2025)',
                    'pharmacist': 'Pharmacist (2025)',
                    'lab assistant': 'Lab Assistant / Lab Technician (2025)',
                    'lab technician': 'Lab Assistant / Lab Technician (2025)',
                    'lab assistant / lab technician': 'Lab Assistant / Lab Technician (2025)',
                    'laboratory assistant': 'Lab Assistant / Lab Technician (2025)',
                    'laboratory technician': 'Lab Assistant / Lab Technician (2025)',
                    
                    # Education
                    'lp school assistant': 'LP / UP School Assistant (2025)',
                    'up school assistant': 'LP / UP School Assistant (2025)',
                    'school assistant': 'LP / UP School Assistant (2025)',
                    'lp / up school assistant': 'LP / UP School Assistant (2025)',
                    'lpsa': 'LP / UP School Assistant (2025)',
                    'upsa': 'LP / UP School Assistant (2025)',
                    'high school assistant': 'High School Assistant (HSA) (2025)',
                    'hsa': 'High School Assistant (HSA) (2025)',
                    'hsa (2025)': 'High School Assistant (HSA) (2025)',
                    'vocational teacher': 'Vocational Teacher (2025)',
                    'higher secondary school teacher': 'Higher Secondary School Teacher (HSST) (2025)',
                    'hsst': 'Higher Secondary School Teacher (HSST) (2025)',
                    'hsst (2025)': 'Higher Secondary School Teacher (HSST) (2025)',
                    'hsst computer science': 'HSST Computer Science (2025)',
                    'computer science': 'HSST Computer Science (2025)',
                    'teacher': 'LP / UP School Assistant (2025)',
                    
                    # VEO
                    'veo': 'Village Extension Officer (VEO) (2025)',
                    'village extension officer': 'Village Extension Officer (VEO) (2025)',
                    'village extension officer (veo)': 'Village Extension Officer (VEO) (2025)',
                    
                    # General
                    'degree level preliminary exam': 'Degree Level Preliminary Exam (2025)',
                    'degree level': 'Degree Level Preliminary Exam (2025)',
                    'preliminary exam': 'Degree Level Preliminary Exam (2025)',
                    'general psc': 'General PSC (2025)',
                    'psc': 'General PSC (2025)',
                    'general': 'General PSC (2025)',
                    
                    # Additional common variations
                    'clerk': 'LD Clerk (LDC) (2025)',
                    'constable': 'Police Constable (2025)',
                    'officer': 'General PSC (2025)',
                    'inspector': 'General PSC (2025)',
                }
                
                # Keep original pattern unchanged
                pattern = re.compile(
                    r'\*{0,2}(\d+)\.\s+(.*?)\s*'  # Question number and text
                    r'```json\s*(\{.*?\})\s*```\s*'  # JSON options
                    r'\*{0,2}Answer:\s*([A-D])\*{0,2}\s*'  # Answer
                    r'(?:\*{0,2}Explanation:\s*(.*?)\s*)?'  # Optional explanation
                    r'\*{0,2}Difficulty:\s*(.*?)\*{0,2}\s*'  # Difficulty
                    r'\*{0,2}Category:\s*(.*?)\s*\|\s*Suitable for:\s*(.*?)(?=\n\n|\*{0,2}\d+\.|\Z)',  # Category and suitable for
                    re.MULTILINE | re.DOTALL
                )
                
                saved_count, error_count, skipped_count = 0, 0, 0
                
                print(f"Input text length: {len(questions_text)}")
                print(f"First 500 chars: {questions_text[:500]}")

                matches = list(pattern.finditer(questions_text))
                print(f"Found {len(matches)} matches")

                for i, match in enumerate(matches):
                    print(f"\n--- Processing Match {i+1} ---")
                    
                    try:
                        question_num = match.group(1)
                        text = match.group(2).strip().rstrip('*').strip()
                        options_json = match.group(3)
                        answer = match.group(4).strip().upper()
                        explanation = match.group(5).strip().strip('*').strip() if match.group(5) else ""
                        difficulty = match.group(6).strip().lower()
                        category_info = match.group(7).strip()
                        suitable_for = match.group(8).strip().rstrip('*').replace('\r', '').replace('\n', '').strip()
                        
                        print(f"Question {question_num}: {text[:50]}...")
                        print(f"Suitable for: '{suitable_for}'")
                        
                        # Check for duplicates
                        if Question.objects.filter(text__iexact=text).exists():
                            print(f"Skipping duplicate: {text[:50]}")
                            skipped_count += 1
                            continue
                        
                        # Parse category - improved topic handling
                        category_name = category_info.split('|')[0].strip()
                        if not category_name:
                            category_name = "General Knowledge"  # Default category
                        
                        # Get or create topic (case-insensitive)
                        topic = Topic.objects.filter(name__iexact=category_name).first()
                        if not topic:
                            topic = Topic.objects.create(name=category_name)
                            print(f"Created new topic: {category_name}")
                        
                        # Parse options JSON
                        try:
                            options = json.loads(options_json)
                        except json.JSONDecodeError as e:
                            raise ValueError(f"Invalid JSON format in options: {e}")
                        
                        # Enhanced exam matching logic
                        exams_to_add = []
                        
                        # Always add to General PSC first for broader accessibility
                        general_psc_exam, created = Exam.objects.get_or_create(
                            name="General PSC (2025)",
                            defaults={
                                'name': "General PSC (2025)", 
                                'year': 2025,
                                'category': ExamCategory.objects.first() or ExamCategory.objects.create(name="PSC", order=1)
                            }
                        )
                        if created:
                            print(f"Created General PSC exam")
                        exams_to_add.append(general_psc_exam)
                        
                        # Process specific exams if mentioned
                        if suitable_for and suitable_for.lower() not in ['general', 'all', 'psc only']:
                            # Split by comma and clean each exam name
                            exam_names = [name.strip() for name in suitable_for.split(',')]
                            print(f"Parsed exam names: {exam_names}")
                            
                            # Check if "All PSC Exams" is present
                            has_all_psc = any(name.lower() in ['all psc exams', 'all psc', 'all psc exams only'] 
                                            for name in exam_names)
                            
                            if has_all_psc:
                                print("Found 'All PSC Exams' - adding all PSC category exams")
                                # For "All PSC Exams", add all PSC category exams
                                psc_category = ExamCategory.objects.filter(name__icontains="PSC").first()
                                if psc_category:
                                    all_psc_exams = Exam.objects.filter(category=psc_category)
                                    exams_to_add.extend(list(all_psc_exams))
                                    print(f"Added {len(all_psc_exams)} PSC exams")
                            
                            # Process ALL exam names (including when "All PSC Exams" is present)
                            # This ensures specific exams like LDC, LGS, VEO are also added
                            for exam_name in exam_names:
                                exam_name_clean = exam_name.strip()
                                exam_name_lower = exam_name_clean.lower()
                                
                                # Skip "All PSC Exams" as it's already processed
                                if exam_name_lower in ['all psc exams', 'all psc', 'all psc exams only']:
                                    continue
                                
                                print(f"Processing exam name: '{exam_name_clean}'")
                                    
                                # Method 1: Direct PSC mapping lookup (highest priority)
                                if exam_name_lower in psc_exam_mapping:
                                    mapped_name = psc_exam_mapping[exam_name_lower]
                                    try:
                                        exam = Exam.objects.get(name=mapped_name)
                                        exams_to_add.append(exam)
                                        print(f"✓ Found PSC mapped exam: {mapped_name}")
                                        continue
                                    except Exam.DoesNotExist:
                                        print(f"✗ PSC mapped exam not found: {mapped_name}")
                                
                                # Method 2: Exact match (case-insensitive)
                                exam_qs = Exam.objects.filter(name__iexact=exam_name_clean)
                                if exam_qs.exists():
                                    exams_to_add.extend(list(exam_qs))
                                    print(f"✓ Found exact match: {exam_name_clean}")
                                    continue
                                
                                # Method 3: Partial match with priority for PSC exams
                                # First try PSC-specific partial matches
                                psc_keywords = ['psc', 'police', 'driver', 'assistant', 'clerk', 'inspector', 'officer', 'constable']
                                exam_qs = Exam.objects.filter(name__icontains=exam_name_clean)
                                
                                if exam_qs.exists():
                                    # Prioritize PSC-related exams
                                    psc_exams = [e for e in exam_qs if any(keyword in e.name.lower() for keyword in psc_keywords)]
                                    if psc_exams:
                                        exams_to_add.extend(psc_exams)
                                        print(f"✓ Found PSC contains match: {[e.name for e in psc_exams]}")
                                    else:
                                        # Add all matching exams if no PSC-specific match
                                        exams_to_add.extend(list(exam_qs))
                                        print(f"✓ Found general contains match: {[e.name for e in exam_qs]}")
                                    continue
                                
                                # Method 4: Fuzzy matching for common abbreviations
                                abbreviation_patterns = {
                                    'si': ['sub inspector', 'inspector'],
                                    'cpo': ['civil police officer', 'police officer'],
                                    'lgs': ['last grade servant', 'servant'],
                                    'ldc': ['clerk', 'division clerk'],
                                    'hsa': ['school assistant', 'assistant'],
                                    'hsst': ['school teacher', 'teacher'],
                                    'veo': ['village extension officer', 'extension officer'],
                                    'jhi': ['health inspector', 'inspector'],
                                }
                                
                                if exam_name_lower in abbreviation_patterns:
                                    for pattern in abbreviation_patterns[exam_name_lower]:
                                        fuzzy_matches = Exam.objects.filter(name__icontains=pattern)
                                        if fuzzy_matches.exists():
                                            exams_to_add.extend(list(fuzzy_matches))
                                            print(f"✓ Found fuzzy match for '{exam_name_clean}': {[e.name for e in fuzzy_matches]}")
                                            break
                                
                                if not any(exam.name for exam in exams_to_add if exam_name_clean.lower() in exam.name.lower()):
                                    print(f"✗ No exam found for: {exam_name_clean}")
                        
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_exams = []
                        for exam in exams_to_add:
                            if exam.id not in seen:
                                seen.add(exam.id)
                                unique_exams.append(exam)
                        exams_to_add = unique_exams
                        
                        print(f"Final exams to add: {[e.name for e in exams_to_add]}")
                        
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
                        question.exams.set(exams_to_add)
                        saved_count += 1
                        print(f"✓ Successfully saved question {question_num}")
                        
                    except Exception as e:
                        error_count += 1
                        error_msg = f"Error processing question {i+1}: {str(e)}"
                        print(f"✗ {error_msg}")
                        print(f"Full traceback: {traceback.format_exc()}")
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
**Category: Your Category | Suitable for: Driver (Light / Heavy) (2025)**

**2. Next question...**
        </pre>
        <h3>PSC Exam Matching:</h3>
        <ul>
            <li><strong>All PSC Exams:</strong> Use "All PSC Exams" or "All PSC" to add to General PSC only (other specific exams in the same list will be ignored)</li>
            <li><strong>Specific exams:</strong> Use exact names like "Driver (Light / Heavy) (2025)", "HSA", "SI", "LDC", "VEO", etc.</li>
            <li><strong>General PSC:</strong> Use "General" for general PSC questions</li>
            <li><strong>Multiple exams:</strong> Separate with commas: "Driver, Police Constable, HSA"</li>
            <li><strong>Abbreviations work:</strong> HSA, LGS, SI, CPO, LDC, VEO, etc.</li>
        </ul>
        <h3>Priority Matching:</h3>
        <ol>
            <li>If "All PSC Exams" is present → Add to General PSC only</li>
            <li>Exact PSC exam name mapping</li>
            <li>Case-insensitive exact match</li>
            <li>PSC-related contains match only</li>
            <li>Default to General PSC if no match found</li>
        </ol>
        <h3>Examples:</h3>
        <ul>
            <li><strong>"All PSC Exams, LDC, HSA"</strong> → Only adds to General PSC</li>
            <li><strong>"LDC, HSA, Driver"</strong> → Adds to specific LDC, HSA, and Driver exams</li>
            <li><strong>"All PSC"</strong> → Adds to General PSC only</li>
        </ul>
        """
        return render(request, 'admin/questionbank/question/bulk_upload.html', context)


@admin.register(ExamSyllabus)
class ExamSyllabusAdmin(admin.ModelAdmin):
    list_display = ('exam', 'topic', 'num_questions')
    list_filter = ('exam',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # Add the new field to the list display
    list_display = ('user', 'institute', 'is_content_creator')
    list_filter = ('institute', 'is_content_creator')
    search_fields = ('user__username', 'institute__name')
    
    # Add the field to the form for editing
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'institute', 'is_content_creator')
        }),
        ('Personal Details', {
            'fields': ('profile_photo', 'qualifications', 'date_of_birth', 'place','bio')
        }),
        ('User Preferences', {
            'fields': ('preferred_difficulty', 'preferred_topics', 'preferred_exams')
        }),
    )


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question_text', 'is_correct', 'answered_at')
    list_filter = ('is_correct', 'answered_at')
    search_fields = ('user__username', 'question__text')
    
    @admin.display(description='Question Text')
    def question_text(self, obj):
        return obj.question.text[:50]


# Register the remaining simple models
admin.site.register(Bookmark)
admin.site.register(Report)

# admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Questions,DailyExam
from .views import BulkUploadView


@admin.register(Questions)
class QuestionsAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'correct_answer', 'option_a', 'option_b')
    search_fields = ('question_text',)
    list_filter = ('correct_answer',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('text-upload/', self.text_upload_view, name='questions_text_upload'),
        ]
        return custom_urls + urls

    def text_upload_view(self, request):
        if request.method == 'POST':
            text_data = request.POST.get('text_data', '').strip()

            if not text_data:
                messages.error(request, 'Please paste some text.')
                return self.render_upload_page(request)

            try:
                bulk_view = BulkUploadView()
                result = bulk_view.process_questions_text(text_data)
                success = len(result['created_questions'])
                failed = len(result['errors'])

                if success:
                    messages.success(request, f'Successfully uploaded {success} questions.')
                if failed:
                    messages.warning(request, f'{failed} lines failed. Errors: {"; ".join(result["errors"][:5])}')
                return redirect('..')

            except Exception as e:
                messages.error(request, f'Upload failed: {e}')

        return self.render_upload_page(request)

    def render_upload_page(self, request):
        return render(request, 'admin/text_upload.html', {
            'title': 'Upload Questions via Text',
            'opts': self.model._meta,
        })

# admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import DailyExam, Questions # CORRECTED: Use the correct model name 'Questions'

@admin.register(DailyExam)
class DailyExamAdmin(admin.ModelAdmin):
    list_display = ('date', 'question_count', 'created_at')
    ordering = ('-date',)
    filter_horizontal = ('questions',)
    search_fields = ('date',)
    date_hierarchy = 'date'

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Number of Questions'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), name='dailyexam_bulk_upload'),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request):
        if request.method == 'POST':
            text_data = request.POST.get('text_data', '').strip()
            exam_date_str = request.POST.get('exam_date', '').strip()

            if not text_data or not exam_date_str:
                self.message_user(request, 'Please provide both a date and question text.', level=messages.ERROR)
                return redirect('.')
            
            try:
                lines = text_data.strip().split('\n')
                created_questions = []
                for line in lines:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 6:
                        # CORRECTED: Use the correct model name 'Questions'
                        question = Questions.objects.create(
                            question_text=parts[0],
                            option_a=parts[1],
                            option_b=parts[2],
                            option_c=parts[3],
                            option_d=parts[4],
                            correct_answer=parts[5].upper(),
                            explanation=parts[6] if len(parts) > 6 else ''
                        )
                        created_questions.append(question)
                
                if created_questions:
                    exam, created = DailyExam.objects.get_or_create(date=exam_date_str)
                    exam.questions.add(*created_questions)
                    self.message_user(request, f"Successfully added {len(created_questions)} questions to Daily Exam for {exam.date}.", level=messages.SUCCESS)
                else:
                    self.message_user(request, "No valid questions were found in the text.", level=messages.WARNING)

            except Exception as e:
                self.message_user(request, f'An error occurred: {e}', level=messages.ERROR)
            
            return redirect('..')

        context = dict(
           self.admin_site.each_context(request),
           title="Bulk Upload for Daily Exam",
        )
        return render(request, "admin/daily_exam_bulk_upload.html", context)
    


# In questionbank/admin.py
from .models import ModelExam,ModelExamAttempt

@admin.register(ModelExam)
class ModelExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'exam', 'question_count')
    list_filter = ('exam',)
    search_fields = ('name',)
    filter_horizontal = ('questions',)

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Number of Questions'

@admin.register(ModelExamAttempt)
class ModelExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'model_exam', 'score', 'submitted_at')
    list_filter = ('model_exam__name',)
    search_fields = ('user__username', 'model_exam__name')



# In questionbank/admin.py
from .models import PreviousYearPaper

@admin.register(PreviousYearPaper)
class PreviousYearPaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam', 'year', 'uploaded_at')
    list_filter = ('exam', 'year')
    search_fields = ('title',)


# In questionbank/admin.py
from .models import Syllabus, ExamAnnouncement

@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = ('exam', 'updated_at')
    search_fields = ('exam__name',)

@admin.register(ExamAnnouncement)
class ExamAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'publication_date')
    list_filter = ('publication_date',)
    search_fields = ('title',)
