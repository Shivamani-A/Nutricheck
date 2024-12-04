from django import forms

class ExcelUploadForm(forms.Form):
    file = forms.FileField()

class ManualInputForm(forms.Form):
    sample = forms.CharField(
        required=True,
        error_messages={"required": "Sample name cannot be empty."},
    )
    protein_percent = forms.FloatField(
        required=True,
        min_value=0,
        max_value=100,
        error_messages={
            "required": "Protein percentage cannot be empty and must be numerical.",
            "min_value": "Protein percentage must be 0 or greater.",
            "max_value": "Protein percentage cannot exceed 100.",
        },
    )
    pdcaas = forms.FloatField(
        required=True,
        min_value=0,
        max_value=100,
        error_messages={
            "required": "PDCAAS cannot be empty and must be numerical.",
            "min_value": "PDCAAS must be 0 or greater.",
            "max_value": "PDCAAS cannot exceed 100.",
        },
    )
    ivpdcaas = forms.FloatField(
        required=True,
        min_value=0,
        max_value=100,
        error_messages={
            "required": "IVPDCAAS cannot be empty and must be numerical.",
            "min_value": "IVPDCAAS must be 0 or greater.",
            "max_value": "IVPDCAAS cannot exceed 100.",
        },
    )


