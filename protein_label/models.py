from django.db import models

# Create your models here.
class ProteinData(models.Model):
    sample = models.CharField(max_length=255)  # Sample name (e.g., Baked Yellow Split Pea)
    protein_percent = models.FloatField()  # Protein percentage
    pdcaas_claim = models.FloatField()  # PDCAAS calculation result
    pdcaas_label = models.CharField(max_length=255)  # PDCAAS label
    ivpdcaas_claim = models.FloatField()  # IVPDCAAS calculation result
    ivpdcaas_label = models.CharField(max_length=255)  # IVPDCAAS label

    def __str__(self):
        return self.sample