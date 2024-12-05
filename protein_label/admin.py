from django.contrib import admin
from .models import RACCValue

@admin.register(RACCValue)
class RACCValueAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'category', 'racc_value')
    search_fields = ('keyword',)
    list_filter = ('category',)