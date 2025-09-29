from django.urls import path
from . import views

app_name = 'versions'

urlpatterns = [
    # Lista de versiones
    path('', views.version_list, name='version_list'),
    
    # Historial de versiones
    path('history/<int:template_id>/', views.version_history, name='version_history'),
    
    # Detalles de versión
    path('detail/<int:version_id>/', views.version_detail, name='version_detail'),
    
    # Comparar versiones
    path('compare/<int:version1_id>/<int:version2_id>/', views.compare_versions, name='compare_versions'),
    
    # Rollback
    path('rollback/<int:version_id>/', views.rollback_version, name='rollback_version'),
    
    # Gestión de ramas
    path('branches/<int:template_id>/', views.branch_management, name='branch_management'),
    path('branch/create/<int:template_id>/', views.create_branch, name='create_branch'),
    path('branch/merge/<int:branch_id>/', views.merge_branch, name='merge_branch'),
    
    # Log de cambios
    path('changelog/<int:template_id>/', views.change_log, name='change_log'),
]