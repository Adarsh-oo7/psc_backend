from django import forms
from .models import Exam, Topic

class BulkQuestionUploadForm(forms.Form):
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.all().order_by('name'),
        required=True,
        label="Select the Exam for these questions"
    )
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.all().order_by('name'), # You can filter this further if needed
        required=True,
        label="Select the Topic for these questions"
    )
    questions_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 25, 'cols': 120}),
        help_text="Paste your formatted questions here. Ensure the format is followed exactly."
    )