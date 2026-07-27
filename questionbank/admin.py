import json
import re
import traceback
import hashlib
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.utils.html import format_html
from django.db.models import Q

# --- Import all necessary models and the form ---
from .models import (
    ExamCategory, Exam, Topic, Question, 
    UserAnswer, Bookmark, Report, UserProfile, ExamSyllabus
)
from .forms import BulkQuestionUploadForm, QuestionForm


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
    form = QuestionForm
    list_display = ('text', 'display_exams', 'topic', 'sub_topic', 'difficulty', 'status', 'source', 'verified', 'is_verified')
    list_filter = ('status', 'source', 'verified', 'is_verified', 'exams', 'topic', 'difficulty', 'institute')
    search_fields = ('text',)
    filter_horizontal = ('exams',)
    readonly_fields = ('text_hash',)
    actions = ['approve_questions', 'reject_questions']

    fieldsets = (
        ('Core Details', {'fields': ('text', 'topic', 'sub_topic')}),
        ('Question Content', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer', 'explanation'),
            'description': """<p style="font-size: 1.1em;">Enter options A, B, C, D and select the correct answer.</p>"""
        }),
        ('Categorization & Difficulty', {'fields': ('difficulty', 'exams', 'institute')}),
        ('Submission Info', {'fields': ('submitted_by', 'status', 'source', 'verified', 'is_verified', 'text_hash')}),
    )

    def approve_questions(self, request, queryset):
        from questionbank.gamification import award_xp
        count = 0
        for question in queryset:
            if question.status != 'approved':
                question.status = 'approved'
                question.verified = True
                question.is_verified = True
                question.save()
                count += 1
                
                # Award XP if submitted by a user
                if question.submitted_by:
                    award_xp(question.submitted_by, 100)
                    approved_count = Question.objects.filter(
                        submitted_by=question.submitted_by,
                        status='approved'
                    ).count()
                    if approved_count >= 10:
                        profile = question.submitted_by.userprofile
                        if not profile.is_content_creator:
                            profile.is_content_creator = True
                            profile.save(update_fields=['is_content_creator'])
        self.message_user(request, f"Successfully approved {count} questions.")
    approve_questions.short_description = "Approve selected questions"

    def reject_questions(self, request, queryset):
        count = 0
        for question in queryset:
            if question.status != 'rejected':
                question.status = 'rejected'
                question.save()
                count += 1
        self.message_user(request, f"Successfully rejected {count} questions.")
    reject_questions.short_description = "Reject selected questions"
    

    def display_exams(self, obj):
        return ", ".join([exam.name for exam in obj.exams.all()])
    display_exams.short_description = 'Exams'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), name='questionbank_question_bulk_upload'),
            path('verification-dashboard/', self.admin_site.admin_view(self.verification_dashboard_view), name='questionbank_question_verification_dashboard'),
            path('<int:question_id>/api/toggle-verify/', self.admin_site.admin_view(self.api_toggle_verify), name='questionbank_question_api_toggle_verify'),
            path('<int:question_id>/api/toggle-status/', self.admin_site.admin_view(self.api_toggle_status), name='questionbank_question_api_toggle_status'),
            path('<int:question_id>/api/delete/', self.admin_site.admin_view(self.api_delete_question), name='questionbank_question_api_delete'),
        ]
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
                        
                        # Parse options JSON
                        try:
                            options = json.loads(options_json)
                        except json.JSONDecodeError as e:
                            raise ValueError(f"Invalid JSON format in options: {e}")

                        # Calculate text hash to check duplicate
                        normalized = re.sub(r'[^\w\s]', '', text).lower().strip()
                        normalized = re.sub(r'\s+', ' ', normalized)
                        if options and isinstance(options, dict):
                            opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options.items()))
                            normalized = f"{normalized}||{opts_str}"
                        text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

                        # Check for duplicates using hash or exact match
                        if Question.objects.filter(Q(text_hash=text_hash) | Q(text__iexact=text)).exists():
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

    def verification_dashboard_view(self, request):
        from django.core.paginator import Paginator
        from django.http import Http404
        
        # Check permissions
        if not self.has_change_permission(request):
            raise Http404("You do not have permission to view this dashboard.")
            
        # Get query parameters
        search_query = request.GET.get('q', '').strip()
        topic_id = request.GET.get('topic', '').strip()
        status_filter = request.GET.get('status', '').strip()
        verify_filter = request.GET.get('verified', '').strip()
        lang_filter = request.GET.get('language', '').strip()
        difficulty_filter = request.GET.get('difficulty', '').strip()
        
        # Start with all questions
        queryset = Question.objects.all().order_by('-id')
        
        # Apply search
        if search_query:
            queryset = queryset.filter(text__icontains=search_query)
            
        # Apply filters
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if verify_filter:
            is_v = verify_filter == '1'
            queryset = queryset.filter(Q(verified=is_v) | Q(is_verified=is_v))
        if lang_filter:
            queryset = queryset.filter(language=lang_filter)
        if difficulty_filter:
            queryset = queryset.filter(difficulty=difficulty_filter)
            
        # Paginator
        paginator = Paginator(queryset, 50)  # 50 per page
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        # Context lists
        topics = Topic.objects.all().order_by('name')
        
        context = dict(
            self.admin_site.each_context(request),
            title="Question Verification Dashboard",
            page_obj=page_obj,
            topics=topics,
            search_query=search_query,
            selected_topic=topic_id,
            selected_status=status_filter,
            selected_verified=verify_filter,
            selected_language=lang_filter,
            selected_difficulty=difficulty_filter,
        )
        return render(request, 'admin/questionbank/question/verification_dashboard.html', context)

    def api_toggle_verify(self, request, question_id):
        from django.http import JsonResponse
        if not self.has_change_permission(request):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        try:
            question = Question.objects.get(pk=question_id)
            new_val = not question.verified
            question.verified = new_val
            question.is_verified = new_val
            question.save()
            return JsonResponse({'success': True, 'verified': new_val})
        except Question.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Question not found'}, status=404)

    def api_toggle_status(self, request, question_id):
        from django.http import JsonResponse
        if not self.has_change_permission(request):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        try:
            question = Question.objects.get(pk=question_id)
            new_status = 'rejected' if question.status == 'approved' else 'approved'
            question.status = new_status
            question.save()
            return JsonResponse({'success': True, 'status': new_status})
        except Question.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Question not found'}, status=404)

    def api_delete_question(self, request, question_id):
        from django.http import JsonResponse
        if not self.has_delete_permission(request):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        try:
            question = Question.objects.get(pk=question_id)
            question.delete()
            return JsonResponse({'success': True})
        except Question.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Question not found'}, status=404)



@admin.register(ExamSyllabus)
class ExamSyllabusAdmin(admin.ModelAdmin):
    list_display = ('exam', 'topic', 'num_questions')
    list_filter = ('exam',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'get_email', 'phone_number', 'is_premium', 
        'total_xp', 'current_streak', 'institute', 
        'get_date_joined', 'get_last_login', 'is_content_creator'
    )
    list_filter = (
        'is_premium', 'is_content_creator', 'district', 
        'institute', 'preferred_language', 'user__date_joined'
    )
    search_fields = ('user__username', 'user__email', 'phone_number', 'institute__name')
    ordering = ('-user__date_joined',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'institute', 'subscription_plan')

    @admin.display(description='Email', ordering='user__email')
    def get_email(self, obj):
        return obj.user.email if obj.user and obj.user.email else '—'

    @admin.display(description='Date Joined', ordering='user__date_joined')
    def get_date_joined(self, obj):
        return obj.user.date_joined if obj.user else None

    @admin.display(description='Last Login', ordering='user__last_login')
    def get_last_login(self, obj):
        return obj.user.last_login if obj.user and obj.user.last_login else None

    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'phone_number', 'institute', 'is_content_creator', 'is_owner')
        }),
        ('Subscription & Status', {
            'fields': ('is_premium', 'subscription_plan', 'subscription_end_date', 'target_exam_date', 'referral_code', 'referred_by')
        }),
        ('Gamification & Activity', {
            'fields': ('total_xp', 'level', 'current_streak', 'longest_streak', 'last_active_date', 'streak_freeze_count')
        }),
        ('Personal Details', {
            'fields': ('profile_photo', 'qualifications', 'date_of_birth', 'place', 'district', 'bio')
        }),
        ('User Preferences', {
            'fields': ('preferred_language', 'preferred_difficulty', 'preferred_topics', 'preferred_exams')
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


# ===================================================================
# --- Report Admin with AI Analyze & Fix ---
# ===================================================================

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'report_type_badge', 'question_preview', 'user',
        'created_at', 'report_count_for_question', 'ai_fix_link'
    )
    list_filter = ('report_type', 'created_at')
    search_fields = ('question__text', 'user__username', 'reason')
    readonly_fields = ('user', 'question', 'report_type', 'reason', 'created_at', 'question_full_preview')
    ordering = ('-created_at',)
    actions = ['ai_analyze_and_fix_selected']

    fieldsets = (
        ('Report Details', {
            'fields': ('user', 'created_at', 'report_type', 'reason')
        }),
        ('Reported Question', {
            'fields': ('question_full_preview',)
        }),
    )

    def report_type_badge(self, obj):
        colors = {
            'wrong_answer': '#EF4444',
            'question_error': '#F59E0B',
            'bad_options': '#8B5CF6',
            'language_issue': '#3B82F6',
            'formatting_issue': '#6B7280',
            'other': '#6B7280',
        }
        color = colors.get(obj.report_type, '#6B7280')
        return format_html(
            '<span style="background:{}20;color:{};border:1px solid {}40;'
            'padding:2px 8px;border-radius:20px;font-size:0.75rem;font-weight:600">{}</span>',
            color, color, color, obj.get_report_type_display()
        )
    report_type_badge.short_description = 'Type'

    def question_preview(self, obj):
        return obj.question.text[:70] + ('...' if len(obj.question.text) > 70 else '')
    question_preview.short_description = 'Question'

    def question_full_preview(self, obj):
        import json
        q = obj.question
        opts = q.options
        if isinstance(opts, str):
            try:
                opts = json.loads(opts)
            except Exception:
                opts = {}
        if not isinstance(opts, dict):
            opts = {}

        correct = str(q.correct_answer or '').strip().upper()
        sorted_opts = sorted(opts.items(), key=lambda x: str(x[0]).upper())
        opts_html_parts = []
        for k, v in sorted_opts:
            key_upper = str(k).upper()
            is_correct = (key_upper == correct)
            style = 'padding:6px 10px;margin-bottom:4px;border-radius:6px;background:#dcfce7;color:#14532d;font-weight:700;border:1px solid #86efac' if is_correct else 'padding:6px 10px;margin-bottom:4px;border-radius:6px;background:#ffffff;border:1px solid #e2e8f0'
            badge = ' &#10003; [Correct Answer]' if is_correct else ''
            opts_html_parts.append(f'<div style="{style}"><strong>{key_upper}.</strong> {v}{badge}</div>')

        opts_html = ''.join(opts_html_parts)
        return format_html(
            '<div style="background:#f8fafc;padding:16px;border-radius:10px;border:1px solid #cbd5e1;max-width:700px">'
            '<p style="font-weight:700;font-size:1.05rem;margin-bottom:12px;color:#0f172a">{}</p>'
            '{}'
            '<p style="margin-top:14px;color:#15803d;font-weight:800"><strong>Marked Correct: Option {}</strong></p>'
            '<p style="color:#334155;font-size:0.9rem;margin-top:6px"><em>Explanation: {}</em></p>'
            '</div>',
            q.text, format_html(opts_html), correct,
            q.explanation[:300] if q.explanation else '(none)'
        )
    question_full_preview.short_description = 'Full Question Preview'

    def report_count_for_question(self, obj):
        count = Report.objects.filter(question=obj.question).count()
        if count >= 3:
            return format_html('<span style="color:#EF4444;font-weight:700">{} reports</span>', count)
        return format_html('<span style="color:#6B7280">{}</span>', count)
    report_count_for_question.short_description = '# Reports'

    def ai_fix_link(self, obj):
        url = f'/admin/questionbank/report/{obj.pk}/ai-fix/'
        return format_html(
            '<a href="{}" style="background:#2E8B57;color:white;padding:4px 10px;'
            'border-radius:6px;font-size:0.75rem;text-decoration:none;font-weight:600">'
            '🤖 AI Fix</a>', url
        )
    ai_fix_link.short_description = 'Action'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:report_id>/ai-fix/',
                self.admin_site.admin_view(self.ai_fix_view),
                name='questionbank_report_ai_fix'
            ),
            path(
                '<int:report_id>/apply-fix/',
                self.admin_site.admin_view(self.apply_fix_view),
                name='questionbank_report_apply_fix'
            ),
        ]
        return custom_urls + urls

    def _call_gemini_fix(self, report):
        """Call AI (Gemini / Groq fallback) with strict PSC formatting prompt. Returns dict or raises."""
        import os, json, requests

        q = report.question
        opts = q.options if isinstance(q.options, dict) else {}
        opts_str = '\n'.join(f'{k}) {v}' for k, v in opts.items())

        prompt = f"""You are a Kerala PSC exam question quality expert.

A user reported this question with the issue type: "{report.get_report_type_display()}"
User's complaint: "{report.reason}"

ORIGINAL QUESTION:
Question Text: {q.text}
Options:
{opts_str}
Correct Answer: {q.correct_answer}
Explanation: {q.explanation or '(none)'}

YOUR TASK:
Analyze the reported issue and return a corrected, high-quality version of this question.

CRITICAL & STRICT RULES:
1. PRESERVE ORIGINAL OPTIONS: Retain the original options A, B, C, D as much as possible! Only modify an option if it has typos, bad formatting, duplicate text, or is factually wrong. DO NOT replace original options with unrelated or random choices.
2. HIGH TOPIC RELEVANCE: All 4 options MUST be strictly relevant, plausible, and belonging to the EXACT same subject category as the question (e.g., if the question is about Kerala History, all options must be relevant Kerala historical figures/places/events).
3. QUESTION TEXT: Fix any grammatical, spelling, or translation errors in the question text while preserving its core topic and meaning. Keep original language (English or Malayalam).
4. EXACTLY 4 OPTIONS: Ensure there are exactly 4 distinct options labeled A, B, C, D.
5. ACCURATE CORRECT ANSWER: Ensure 'correct_answer' is a single uppercase letter ('A', 'B', 'C', or 'D') that points to the genuinely correct option.
6. CLEAR EXPLANATION: Provide a helpful explanation explaining why the correct option is right and clarifying any confusion mentioned in the user report.

RETURN ONLY THIS JSON (no markdown, no extra text):
{{
  "question_text": "corrected question text here",
  "options": {{"A": "option text", "B": "option text", "C": "option text", "D": "option text"}},
  "correct_answer": "A",
  "explanation": "clear explanation here"
}}"""

        raw_json = None
        last_error = None

        # 1. Try Gemini API Keys and Models
        gemini_keys = [k for k in [os.environ.get('GEMINI_REPORT_API_KEY'), os.environ.get('GEMINI_API_KEY')] if k]
        gemini_models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']

        for key in gemini_keys:
            if raw_json: break
            for model_name in gemini_models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
                    payload = {'contents': [{'parts': [{'text': prompt}]}]}
                    res = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=20)
                    if res.status_code == 200:
                        raw_json = res.json()['candidates'][0]['content']['parts'][0]['text']
                        break
                    else:
                        last_error = f"Gemini ({model_name}): HTTP {res.status_code}"
                except Exception as e:
                    last_error = f"Gemini error: {e}"

        # 2. Fallback to Groq API if Gemini failed or rate limited
        if not raw_json and os.environ.get('GROQ_API_KEY'):
            try:
                groq_key = os.environ.get('GROQ_API_KEY')
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }
                res = requests.post(url, json=payload, headers=headers, timeout=20)
                if res.status_code == 200:
                    raw_json = res.json()['choices'][0]['message']['content']
                else:
                    last_error = f"Groq API: HTTP {res.status_code}"
            except Exception as e:
                last_error = f"Groq API error: {e}"

        # 3. Fallback to OpenAI API if both Gemini and Groq failed
        if not raw_json and os.environ.get('OPENAI_API_KEY'):
            try:
                openai_key = os.environ.get('OPENAI_API_KEY')
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }
                res = requests.post(url, json=payload, headers=headers, timeout=20)
                if res.status_code == 200:
                    raw_json = res.json()['choices'][0]['message']['content']
                else:
                    last_error = f"OpenAI API: HTTP {res.status_code}"
            except Exception as e:
                last_error = f"OpenAI API error: {e}"

        if not raw_json:
            raise ValueError(f"Could not generate AI fix. {last_error or 'Please check API keys (GEMINI_API_KEY / GROQ_API_KEY / OPENAI_API_KEY).'}")

        # Strip markdown code fences if present
        raw_json = raw_json.strip()
        if raw_json.startswith('```'):
            raw_json = raw_json.split('```')[1]
            if raw_json.startswith('json'):
                raw_json = raw_json[4:]

        result = json.loads(raw_json.strip())

        # Validate required fields
        required = ['question_text', 'options', 'correct_answer', 'explanation']
        for field in required:
            if field not in result:
                raise ValueError(f"AI response missing field: {field}")

        # Validate options have A, B, C, D
        if set(result['options'].keys()) != {'A', 'B', 'C', 'D'}:
            raise ValueError(f"AI options must have exactly A, B, C, D — got {list(result['options'].keys())}")

        # Validate correct_answer
        if result['correct_answer'].upper() not in ('A', 'B', 'C', 'D'):
            raise ValueError(f"AI correct_answer must be A/B/C/D — got '{result['correct_answer']}'")

        result['correct_answer'] = result['correct_answer'].upper()
        return result

    def ai_fix_view(self, request, report_id):
        """Show AI-suggested fix side by side with original."""
        from django.http import HttpResponse

        try:
            report = Report.objects.select_related('question', 'user').get(pk=report_id)
        except Report.DoesNotExist:
            messages.error(request, 'Report not found.')
            return redirect('..')

        ai_result = None
        ai_error = None

        if request.method == 'POST':
            try:
                ai_result = self._call_gemini_fix(report)
                # Store in session for apply step
                request.session[f'ai_fix_{report_id}'] = ai_result
            except Exception as e:
                ai_error = str(e)
                import traceback
                ai_error += '\n' + traceback.format_exc()

        elif request.method == 'GET':
            # Check if we already generated
            ai_result = request.session.get(f'ai_fix_{report_id}')

        context = dict(
            self.admin_site.each_context(request),
            title=f'AI Fix — Report #{report_id}',
            report=report,
            question=report.question,
            ai_result=ai_result,
            ai_error=ai_error,
            opts=self.model._meta,
        )
        return render(request, 'admin/questionbank/report/ai_fix.html', context)

    def merge_duplicate_questions(self, existing_q, duplicate_q):
        """Merges duplicate_q into existing_q, re-pointing all relationships, and deletes duplicate_q."""
        from django.db import transaction
        from .models import (
            UserAnswer, Bookmark, Report, DailyExam, ModelExam, 
            PreviousYearPaper, SessionAnswer, AIExplanationCache
        )

        with transaction.atomic():
            # 1. UserAnswer
            UserAnswer.objects.filter(question=duplicate_q).update(question=existing_q)
            
            # 2. Bookmark
            for b in Bookmark.objects.filter(question=duplicate_q):
                if not Bookmark.objects.filter(user=b.user, question=existing_q).exists():
                    b.question = existing_q
                    b.save()
                else:
                    b.delete()

            # 3. Report
            Report.objects.filter(question=duplicate_q).update(question=existing_q)

            # 4. DailyExam (ManyToMany)
            for de in DailyExam.objects.filter(questions=duplicate_q):
                de.questions.remove(duplicate_q)
                de.questions.add(existing_q)

            # 5. ModelExam (ManyToMany)
            for me in ModelExam.objects.filter(questions=duplicate_q):
                me.questions.remove(duplicate_q)
                me.questions.add(existing_q)

            # 6. PreviousYearPaper (ManyToMany)
            for pyp in PreviousYearPaper.objects.filter(questions=duplicate_q):
                pyp.questions.remove(duplicate_q)
                pyp.questions.add(existing_q)

            # 7. SessionAnswer (Inline Session Answers)
            for sa in SessionAnswer.objects.filter(question=duplicate_q):
                if not SessionAnswer.objects.filter(session=sa.session, question=existing_q).exists():
                    sa.question = existing_q
                    sa.save()
                else:
                    sa.delete()

            # 8. AIExplanationCache
            for cache in AIExplanationCache.objects.filter(question=duplicate_q):
                if not AIExplanationCache.objects.filter(question=existing_q, language=cache.language).exists():
                    cache.question = existing_q
                    cache.save()
                else:
                    cache.delete()

            # 9. Update stats on existing_q
            existing_q.times_answered += duplicate_q.times_answered
            existing_q.times_correct += duplicate_q.times_correct
            existing_q.times_appeared += duplicate_q.times_appeared
            existing_q.save()

            # 10. Delete duplicate_q
            duplicate_q.delete()

    def apply_fix_view(self, request, report_id):
        """Apply the AI fix to the actual question."""
        if request.method != 'POST':
            return redirect(f'/admin/questionbank/report/{report_id}/ai-fix/')

        try:
            report = Report.objects.select_related('question').get(pk=report_id)
        except Report.DoesNotExist:
            messages.error(request, 'Report not found.')
            return redirect('/admin/questionbank/report/')

        ai_result = request.session.get(f'ai_fix_{report_id}')
        if not ai_result:
            messages.error(request, 'No AI result found. Please generate the fix first.')
            return redirect(f'/admin/questionbank/report/{report_id}/ai-fix/')

        try:
            q = report.question
            
            # Compute new text hash beforehand to check for duplicates
            import re, hashlib, json
            normalized = re.sub(r'[^\w\s]', '', ai_result['question_text']).lower().strip()
            normalized = re.sub(r'\s+', ' ', normalized)
            if ai_result['options'] and isinstance(ai_result['options'], dict):
                opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(ai_result['options'].items()))
                normalized = f"{normalized}||{opts_str}"
            new_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()

            # Check if another question with the exact same hash already exists
            existing_q = Question.objects.filter(text_hash=new_hash).exclude(pk=q.pk).first()

            if existing_q:
                # Merge duplicate question (points all answers/bookmarks/exams to existing_q and deletes q)
                self.merge_duplicate_questions(existing_q, q)
                
                # Delete reports pointing to the duplicate question since it was resolved
                Report.objects.filter(question=existing_q).delete()
                
                messages.success(
                    request,
                    f'✅ Question #{q.id} was fixed by AI and matched existing Question #{existing_q.id}. '
                    f'Duplicate question #{q.id} was safely merged and all reports resolved!'
                )
            else:
                # Apply the fix directly
                q.text = ai_result['question_text']
                q.options = ai_result['options']
                q.correct_answer = ai_result['correct_answer']
                q.explanation = ai_result['explanation']
                q.save()

                # Delete this report (and all other reports for same question) once fixed
                Report.objects.filter(question=q).delete()

                messages.success(
                    request,
                    f'✅ Question #{q.id} has been fixed by AI and all related reports have been cleared.'
                )

            # Clean up session
            request.session.pop(f'ai_fix_{report_id}', None)

        except Exception as e:
            messages.error(request, f'Error applying fix: {e}')
            return redirect(f'/admin/questionbank/report/{report_id}/ai-fix/')

        return redirect('/admin/questionbank/report/')

    def ai_analyze_and_fix_selected(self, request, queryset):
        """Bulk action: redirect to AI fix page for each selected report (one at a time)."""
        first = queryset.first()
        if first:
            return redirect(f'/admin/questionbank/report/{first.pk}/ai-fix/')
        self.message_user(request, 'No reports selected.', messages.WARNING)
    ai_analyze_and_fix_selected.short_description = '🤖 AI Analyze & Fix (first selected)'



# admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import DailyExam, Question, Topic

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
                default_topic = Topic.objects.get_or_create(name="General", defaults={'slug': 'general'})[0]
                for line in lines:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 6:
                        text = parts[0]
                        
                        # Construct options dictionary first
                        options = {
                            'A': parts[1],
                            'B': parts[2],
                            'C': parts[3],
                            'D': parts[4],
                        }
                        
                        # Calculate text hash to check duplicate
                        normalized = re.sub(r'[^\w\s]', '', text).lower().strip()
                        normalized = re.sub(r'\s+', ' ', normalized)
                        if options and isinstance(options, dict):
                            opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options.items()))
                            normalized = f"{normalized}||{opts_str}"
                        text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
                        
                        # Check if duplicate question already exists, if so reuse it
                        question = Question.objects.filter(Q(text_hash=text_hash) | Q(text__iexact=text)).first()
                        if not question:
                            question = Question.objects.create(
                                text=text,
                                options=options,
                                correct_answer=parts[5].upper(),
                                explanation=parts[6] if len(parts) > 6 else '',
                                topic=default_topic,
                                difficulty='medium'
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
    list_display = ('title', 'exam', 'year', 'question_count_display', 'uploaded_at')
    list_filter = ('exam', 'year')
    search_fields = ('title',)
    filter_horizontal = ('questions',)

    def question_count_display(self, obj):
        return obj.questions.count()
    question_count_display.short_description = 'Linked Questions'


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


from .models import StudyFeedCard, UserFeedView, AIExplanationCache

@admin.register(StudyFeedCard)
class StudyFeedCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'card_type', 'title', 'created_at')
    list_filter = ('card_type',)
    search_fields = ('title',)

@admin.register(UserFeedView)
class UserFeedViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'card', 'viewed_date')
    list_filter = ('viewed_date',)
    search_fields = ('user__username',)

@admin.register(AIExplanationCache)
class AIExplanationCacheAdmin(admin.ModelAdmin):
    list_display = ('question', 'language', 'created_at')
    list_filter = ('language',)
    search_fields = ('question__text',)


# ===================================================================
# --- Study Flow & Analytics Admin ---
# ===================================================================
from .models import TopicProgress, PracticeSession, SessionAnswer


class SessionAnswerInline(admin.TabularInline):
    model = SessionAnswer
    extra = 0
    readonly_fields = ('question', 'selected_option', 'is_correct', 'time_spent_secs')
    can_delete = False


@admin.register(TopicProgress)
class TopicProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'accuracy_display', 'total_attempted', 'is_weak_area_display', 'last_practiced')
    list_filter = ('topic',)
    search_fields = ('user__username', 'topic__name')
    readonly_fields = ('user', 'topic', 'total_attempted', 'total_correct',
                       'easy_attempted', 'easy_correct', 'medium_attempted', 'medium_correct',
                       'hard_attempted', 'hard_correct')

    @admin.display(description='Accuracy')
    def accuracy_display(self, obj):
        return f"{obj.accuracy}%"

    @admin.display(description='Weak Area?', boolean=True)
    def is_weak_area_display(self, obj):
        return obj.is_weak_area


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_type', 'topic', 'score_display', 'total_questions', 'started_at', 'completed_at')
    list_filter = ('session_type', 'topic')
    search_fields = ('user__username',)
    inlines = [SessionAnswerInline]
    readonly_fields = ('user', 'session_type', 'topic', 'difficulty', 'started_at', 'completed_at',
                       'total_questions', 'correct_count', 'time_taken_secs')

    @admin.display(description='Score')
    def score_display(self, obj):
        return f"{obj.score_percent}%"
