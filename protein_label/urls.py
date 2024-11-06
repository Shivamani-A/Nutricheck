from django.urls import path
from . import views

urlpatterns = [
    path('', views.process_excel, name='process_excel'),
path('download/csv/', views.download_csv, name='download_csv'),
path('download/pdf/', views.download_pdf, name='download_pdf'),
]