from django.db import models

# Create your models here.

class RACCValue(models.Model):
    CATEGORY_CHOICES = [
        ('FLOURS', 'Flours'),
        ('CEREALS','Cereals'),
        ('LEGUMES', 'Legumes'),
    ]

    keyword = models.CharField(max_length=100, unique=True)  # e.g., 'lentil', 'wheat'
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)  # e.g., 'LEGUMES'
    racc_value = models.FloatField()  # e.g., 35

    def __str__(self):
        return f"{self.keyword} ({self.category}) - {self.racc_value}"



class ProteinData(models.Model):
    sample = models.CharField(max_length=255)  # Sample name (e.g., Baked Yellow Split Pea)
    protein_percent = models.FloatField()  # Protein percentage
    pdcaas_claim = models.FloatField()  # PDCAAS calculation result
    pdcaas_label = models.CharField(max_length=255)  # PDCAAS label
    ivpdcaas_claim = models.FloatField()  # IVPDCAAS calculation result
    ivpdcaas_label = models.CharField(max_length=255)  # IVPDCAAS label

    def __str__(self):
        return self.sample