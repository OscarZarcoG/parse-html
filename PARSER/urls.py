from django.urls import path
from . import views

app_name = 'parser'

urlpatterns = [
    # Gestión de documentos
    path('', views.document_list, name='document_list'),
    path('upload/', views.upload_document, name='upload_document'),
    path('<int:document_id>/', views.document_detail, name='document_detail'),
    path('<int:document_id>/delete/', views.delete_document, name='delete_document'),
    path('<int:document_id>/edit/', views.edit_document, name='edit_document'),
    
    # Procesamiento de documentos
    path('<int:document_id>/reprocess/', views.reprocess_document, name='reprocess_document'),
    
    # Vista previa y exportación
    path('<int:document_id>/preview/', views.document_preview, name='document_preview'),
    path('<int:document_id>/export/', views.export_template_files, name='export_template_files'),
]