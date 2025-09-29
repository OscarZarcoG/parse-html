from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import os

from AUTH.models import UserCustom
from PARSER.models import Document
from TEMPLATES.models import Template, TemplateCategory


def home(request):
    """Vista principal - redirige al dashboard si está autenticado"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('auth:login')


@login_required
def dashboard(request):
    """Dashboard principal del usuario"""
    user = request.user
    
    # Estadísticas del usuario
    user_documents = Document.objects.filter(uploaded_by=user)
    user_templates = Template.objects.filter(created_by=user)
    
    stats = {
        'total_documents': user_documents.count(),
        'processed_documents': user_documents.filter(status='processed').count(),
        'processing_documents': user_documents.filter(status='processing').count(),
        'total_templates': user_templates.count(),
        'storage_used': sum(doc.file_size or 0 for doc in user_documents),
        'storage_limit': 1024 * 1024 * 1024,  # 1GB por usuario
    }
    
    # Calcular porcentaje de uso de almacenamiento
    stats['storage_percentage'] = (stats['storage_used'] / stats['storage_limit']) * 100 if stats['storage_limit'] > 0 else 0
    
    # Actividad reciente
    recent_documents = user_documents.order_by('-created_at')[:5]
    recent_templates = user_templates.order_by('-created_at')[:5]
    
    # Cola de procesamiento
    processing_queue = user_documents.filter(
        status__in=['uploading', 'processing', 'parsing']
    ).order_by('-created_at')
    
    # Categorías de plantillas
    categories = TemplateCategory.objects.filter(
        Q(created_by=user) | Q(created_by__isnull=True)
    ).annotate(template_count=Count('template'))
    
    context = {
        'stats': stats,
        'recent_documents': recent_documents,
        'recent_templates': recent_templates,
        'processing_queue': processing_queue,
        'categories': categories,
        'user': user,
    }
    
    return render(request, 'dashboard.html', context)