from django import forms

class ExcelUploadForm(forms.Form):
    file = forms.FileField()

class ManualInputForm(forms.Form):
    sample = forms.CharField(label="Sample Name", max_length=255)
    protein_percent = forms.FloatField(label="Protein %")
    pdcaas = forms.FloatField(label="PDCAAS (%)")
    ivpdcaas = forms.FloatField(label="IVPDCAAS (%)")
