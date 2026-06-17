from django import forms
from .models import Question
import re
import hashlib

class BulkQuestionUploadForm(forms.Form):
    """
    A simplified form for the bulk uploader. It only needs one field
    for the user to paste all their formatted text.
    """
    questions_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 30, 'style': 'width: 100%;'}),
        label="Formatted Questions Text",
        help_text="Paste your questions here. The system will auto-detect the Topic and suitable Exams from the text."
    )


class QuestionForm(forms.ModelForm):
    option_a = forms.CharField(
        max_length=1000, 
        required=True, 
        label="Option A", 
        widget=forms.TextInput(attrs={'style': 'width: 100%;'})
    )
    option_b = forms.CharField(
        max_length=1000, 
        required=True, 
        label="Option B", 
        widget=forms.TextInput(attrs={'style': 'width: 100%;'})
    )
    option_c = forms.CharField(
        max_length=1000, 
        required=True, 
        label="Option C", 
        widget=forms.TextInput(attrs={'style': 'width: 100%;'})
    )
    option_d = forms.CharField(
        max_length=1000, 
        required=True, 
        label="Option D", 
        widget=forms.TextInput(attrs={'style': 'width: 100%;'})
    )

    class Meta:
        model = Question
        fields = '__all__'
        widgets = {
            'options': forms.HiddenInput(),  # Hide original JSON field
            'text': forms.Textarea(attrs={'rows': 3, 'style': 'width: 100%;'}),
            'explanation': forms.Textarea(attrs={'rows': 3, 'style': 'width: 100%;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate initial option fields if options exist
        if self.instance and self.instance.pk and self.instance.options:
            opts = self.instance.options
            if isinstance(opts, str):
                try:
                    import json
                    opts = json.loads(opts)
                except Exception:
                    opts = {}
            if isinstance(opts, dict):
                self.initial['option_a'] = opts.get('A', '')
                self.initial['option_b'] = opts.get('B', '')
                self.initial['option_c'] = opts.get('C', '')
                self.initial['option_d'] = opts.get('D', '')
        
        # Override correct_answer to be a ChoiceField selector
        self.fields['correct_answer'] = forms.ChoiceField(
            choices=[('A', 'Option A'), ('B', 'Option B'), ('C', 'Option C'), ('D', 'Option D')],
            label="Correct Answer"
        )

    def clean(self):
        cleaned_data = super().clean()
        text = cleaned_data.get('text', '')
        
        # Duplicate detection (case-insensitive text normalization hash)
        if text:
            opt_a = cleaned_data.get('option_a')
            opt_b = cleaned_data.get('option_b')
            opt_c = cleaned_data.get('option_c')
            opt_d = cleaned_data.get('option_d')
            
            normalized = re.sub(r'[^\w\s]', '', text).lower().strip()
            normalized = re.sub(r'\s+', ' ', normalized)
            
            if opt_a and opt_b and opt_c and opt_d:
                options_dict = {
                    'A': opt_a,
                    'B': opt_b,
                    'C': opt_c,
                    'D': opt_d
                }
                opts_str = "|".join(f"{k}:{str(v).lower().strip()}" for k, v in sorted(options_dict.items()))
                normalized = f"{normalized}||{opts_str}"
                
            text_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
            
            qs = Question.objects.filter(text_hash=text_hash)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('text', "A duplicate question with similar text already exists in the database.")
        
        # Combine option fields into the options JSON field
        opt_a = cleaned_data.get('option_a')
        opt_b = cleaned_data.get('option_b')
        opt_c = cleaned_data.get('option_c')
        opt_d = cleaned_data.get('option_d')
        
        if opt_a and opt_b and opt_c and opt_d:
            cleaned_data['options'] = {
                'A': opt_a,
                'B': opt_b,
                'C': opt_c,
                'D': opt_d
            }
        else:
            cleaned_data['options'] = {}
            
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.options = self.cleaned_data.get('options', {})
        if commit:
            instance.save()
            self.save_m2m()
        return instance