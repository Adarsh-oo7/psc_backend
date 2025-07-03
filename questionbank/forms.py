from django import forms

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