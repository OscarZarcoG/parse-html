from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
import json
import difflib
from datetime import datetime

from .models import TemplateVersion, Branch, ChangeLog
from TEMPLATES.models import Template
from AUTH.models import UserCustom

@login_required
def version_list(request):
    """
    Lista general de versiones de todas las plantillas del usuario
    """
    # Obtener todas las versiones de plantillas del usuario
    versions = TemplateVersion.objects.filter(
        template__created_by=request.user
    ).order_by('-created_at')
    
    # Filtros
    template_filter = request.GET.get('template')
    if template_filter:
        versions = versions.filter(template_id=template_filter)
    
    # Paginación
    paginator = Paginator(versions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Plantillas del usuario para el filtro
    user_templates = Template.objects.filter(created_by=request.user)
    
    context = {
        'page_obj': page_obj,
        'user_templates': user_templates,
        'current_template': template_filter,
        'total_versions': versions.count()
    }
    
    return render(request, 'versions/version_list.html', context)

@login_required
def version_history(request, template_id):
    """
    Muestra el historial de versiones de una plantilla
    """
    template = get_object_or_404(Template, id=template_id)
    
    # Verificar permisos
    if not template.can_user_view(request.user):
        messages.error(request, 'No tienes permisos para ver esta plantilla.')
        return redirect('templates:template_list')
    
    # Obtener versiones con paginación
    versions = TemplateVersion.objects.filter(template=template).order_by('-created_at')
    
    # Filtros
    branch_filter = request.GET.get('branch')
    if branch_filter:
        versions = versions.filter(branch_name=branch_filter)
    
    author_filter = request.GET.get('author')
    if author_filter:
        versions = versions.filter(author__username__icontains=author_filter)
    
    # Paginación
    paginator = Paginator(versions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener ramas disponibles
    branches = Branch.objects.filter(template=template).order_by('name')
    
    context = {
        'template': template,
        'page_obj': page_obj,
        'branches': branches,
        'current_branch': branch_filter,
        'current_author': author_filter,
        'total_versions': versions.count()
    }
    
    return render(request, 'versions/version_history.html', context)

@login_required
def version_detail(request, version_id):
    """
    Muestra los detalles de una versión específica
    """
    version = get_object_or_404(TemplateVersion, id=version_id)
    
    # Verificar permisos
    if not version.template.can_user_view(request.user):
        messages.error(request, 'No tienes permisos para ver esta versión.')
        return redirect('templates:template_list')
    
    # Obtener cambios relacionados
    change_logs = ChangeLog.objects.filter(version=version).order_by('-timestamp')
    
    # Obtener versión anterior para comparación
    previous_version = TemplateVersion.objects.filter(
        template=version.template,
        version_number__lt=version.version_number
    ).order_by('-version_number').first()
    
    context = {
        'version': version,
        'template': version.template,
        'change_logs': change_logs,
        'previous_version': previous_version,
        'can_edit': version.template.can_user_edit(request.user)
    }
    
    return render(request, 'versions/version_detail.html', context)

@login_required
def compare_versions(request, version1_id, version2_id):
    """
    Compara dos versiones de una plantilla
    """
    version1 = get_object_or_404(TemplateVersion, id=version1_id)
    version2 = get_object_or_404(TemplateVersion, id=version2_id)
    
    # Verificar que pertenecen a la misma plantilla
    if version1.template != version2.template:
        messages.error(request, 'No se pueden comparar versiones de diferentes plantillas.')
        return redirect('versions:version_history', template_id=version1.template.id)
    
    # Verificar permisos
    if not version1.template.can_user_view(request.user):
        messages.error(request, 'No tienes permisos para ver estas versiones.')
        return redirect('templates:template_list')
    
    # Generar comparaciones
    html_diff = generate_diff(version1.html_content, version2.html_content, 'HTML')
    css_diff = generate_diff(version1.css_content, version2.css_content, 'CSS')
    js_diff = generate_diff(version1.js_content, version2.js_content, 'JavaScript')
    
    # Guardar comparación en la base de datos
    comparison = VersionComparison.objects.create(
        version1=version1,
        version2=version2,
        comparison_data={
            'html_changes': count_changes(html_diff),
            'css_changes': count_changes(css_diff),
            'js_changes': count_changes(js_diff)
        },
        compared_by=request.user
    )
    
    context = {
        'version1': version1,
        'version2': version2,
        'template': version1.template,
        'html_diff': html_diff,
        'css_diff': css_diff,
        'js_diff': js_diff,
        'comparison': comparison
    }
    
    return render(request, 'versions/compare_versions.html', context)

@login_required
@require_http_methods(["POST"])
def rollback_version(request, version_id):
    """
    Revierte a una versión anterior
    """
    target_version = get_object_or_404(TemplateVersion, id=version_id)
    template = target_version.template
    
    # Verificar permisos
    if not template.can_user_edit(request.user):
        return JsonResponse({'error': 'No tienes permisos para editar esta plantilla'}, status=403)
    
    try:
        # Crear nueva versión basada en la versión objetivo
        current_version = template.get_current_version()
        new_version_number = current_version.version_number + 1 if current_version else 1
        
        rollback_version = TemplateVersion.objects.create(
            template=template,
            version_number=new_version_number,
            branch_name=target_version.branch_name,
            html_content=target_version.html_content,
            css_content=target_version.css_content,
            js_content=target_version.js_content,
            commit_message=f'Rollback a versión {target_version.version_number}',
            changes_summary={
                'type': 'rollback',
                'target_version': target_version.version_number,
                'rollback_reason': request.POST.get('reason', 'Sin razón especificada')
            },
            author=request.user,
            status='committed',
            is_current=True
        )
        
        # Actualizar versión actual en la plantilla
        if current_version:
            current_version.is_current = False
            current_version.save()
        
        # Actualizar contenido de la plantilla
        template.html_content = target_version.html_content
        template.css_content = target_version.css_content
        template.js_content = target_version.js_content
        template.save()
        
        # Registrar en el log de cambios
        ChangeLog.objects.create(
            template=template,
            version=rollback_version,
            action='rollback',
            description=f'Rollback a versión {target_version.version_number}',
            changes_detail={
                'target_version': target_version.version_number,
                'target_commit': target_version.commit_message,
                'reason': request.POST.get('reason', 'Sin razón especificada')
            },
            affected_files=['html', 'css', 'js'],
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Rollback exitoso a versión {target_version.version_number}',
            'new_version_id': rollback_version.id,
            'redirect_url': f'/templates/{template.id}/editor/'
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Error durante el rollback: {str(e)}'}, status=500)

@login_required
def branch_management(request, template_id):
    """
    Gestión de ramas de una plantilla
    """
    template = get_object_or_404(Template, id=template_id)
    
    # Verificar permisos
    if not template.can_user_edit(request.user):
        messages.error(request, 'No tienes permisos para gestionar las ramas de esta plantilla.')
        return redirect('templates:template_detail', template_id=template.id)
    
    branches = Branch.objects.filter(template=template).order_by('name')
    
    context = {
        'template': template,
        'branches': branches
    }
    
    return render(request, 'versions/branch_management.html', context)

@login_required
@require_http_methods(["POST"])
def create_branch(request, template_id):
    """
    Crea una nueva rama
    """
    template = get_object_or_404(Template, id=template_id)
    
    # Verificar permisos
    if not template.can_user_edit(request.user):
        return JsonResponse({'error': 'No tienes permisos para crear ramas'}, status=403)
    
    branch_name = request.POST.get('branch_name', '').strip()
    description = request.POST.get('description', '').strip()
    base_version_id = request.POST.get('base_version_id')
    
    if not branch_name:
        return JsonResponse({'error': 'El nombre de la rama es requerido'}, status=400)
    
    # Verificar que no existe una rama con el mismo nombre
    if Branch.objects.filter(template=template, name=branch_name).exists():
        return JsonResponse({'error': 'Ya existe una rama con ese nombre'}, status=400)
    
    try:
        # Obtener versión base
        if base_version_id:
            base_version = get_object_or_404(TemplateVersion, id=base_version_id, template=template)
        else:
            base_version = template.get_current_version()
        
        # Crear rama
        branch = Branch.objects.create(
            template=template,
            name=branch_name,
            description=description,
            base_version=base_version,
            created_by=request.user,
            is_main=False
        )
        
        # Registrar en el log
        ChangeLog.objects.create(
            template=template,
            version=base_version,
            action='branch_create',
            description=f'Rama "{branch_name}" creada',
            changes_detail={
                'branch_name': branch_name,
                'base_version': base_version.version_number if base_version else None,
                'description': description
            },
            affected_files=[],
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Rama "{branch_name}" creada exitosamente',
            'branch_id': branch.id
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Error al crear la rama: {str(e)}'}, status=500)

@login_required
@require_http_methods(["POST"])
def merge_branch(request, branch_id):
    """
    Fusiona una rama con la rama principal
    """
    branch = get_object_or_404(Branch, id=branch_id)
    template = branch.template
    
    # Verificar permisos
    if not template.can_user_edit(request.user):
        return JsonResponse({'error': 'No tienes permisos para fusionar ramas'}, status=403)
    
    # No se puede fusionar la rama principal
    if branch.is_main:
        return JsonResponse({'error': 'No se puede fusionar la rama principal'}, status=400)
    
    try:
        # Obtener la última versión de la rama
        branch_version = TemplateVersion.objects.filter(
            template=template,
            branch_name=branch.name
        ).order_by('-version_number').first()
        
        if not branch_version:
            return JsonResponse({'error': 'La rama no tiene versiones para fusionar'}, status=400)
        
        # Obtener rama principal
        main_branch = Branch.objects.get(template=template, is_main=True)
        current_main_version = template.get_current_version()
        
        # Crear nueva versión en la rama principal
        new_version_number = current_main_version.version_number + 1 if current_main_version else 1
        
        merged_version = TemplateVersion.objects.create(
            template=template,
            version_number=new_version_number,
            branch_name=main_branch.name,
            html_content=branch_version.html_content,
            css_content=branch_version.css_content,
            js_content=branch_version.js_content,
            commit_message=f'Merge rama "{branch.name}" - {branch_version.commit_message}',
            changes_summary={
                'type': 'merge',
                'source_branch': branch.name,
                'source_version': branch_version.version_number,
                'merge_strategy': 'fast-forward'
            },
            author=request.user,
            status='committed',
            is_current=True
        )
        
        # Actualizar versión actual
        if current_main_version:
            current_main_version.is_current = False
            current_main_version.save()
        
        # Actualizar contenido de la plantilla
        template.html_content = branch_version.html_content
        template.css_content = branch_version.css_content
        template.js_content = branch_version.js_content
        template.save()
        
        # Marcar rama como fusionada
        branch.is_merged = True
        branch.merged_at = datetime.now()
        branch.merged_by = request.user
        branch.save()
        
        # Registrar en el log
        ChangeLog.objects.create(
            template=template,
            version=merged_version,
            action='merge',
            description=f'Rama "{branch.name}" fusionada con main',
            changes_detail={
                'source_branch': branch.name,
                'source_version': branch_version.version_number,
                'target_branch': main_branch.name,
                'merge_type': 'fast-forward'
            },
            affected_files=['html', 'css', 'js'],
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Rama "{branch.name}" fusionada exitosamente',
            'merged_version_id': merged_version.id
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Error durante la fusión: {str(e)}'}, status=500)

def generate_diff(content1, content2, file_type):
    """
    Genera un diff entre dos contenidos
    """
    lines1 = content1.splitlines(keepends=True) if content1 else []
    lines2 = content2.splitlines(keepends=True) if content2 else []
    
    diff = list(difflib.unified_diff(
        lines1, 
        lines2, 
        fromfile=f'Versión anterior ({file_type})',
        tofile=f'Versión nueva ({file_type})',
        lineterm=''
    ))
    
    return diff

def count_changes(diff_lines):
    """
    Cuenta las líneas añadidas y eliminadas en un diff
    """
    added = 0
    removed = 0
    
    for line in diff_lines:
        if line.startswith('+') and not line.startswith('+++'):
            added += 1
        elif line.startswith('-') and not line.startswith('---'):
            removed += 1
    
    return {'added': added, 'removed': removed}

@login_required
def change_log(request, template_id):
    """
    Muestra el log de cambios de una plantilla
    """
    template = get_object_or_404(Template, id=template_id)
    
    # Verificar permisos
    if not template.can_user_view(request.user):
        messages.error(request, 'No tienes permisos para ver el log de cambios.')
        return redirect('templates:template_list')
    
    # Obtener logs con filtros
    logs = ChangeLog.objects.filter(template=template).order_by('-timestamp')
    
    action_filter = request.GET.get('action')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    user_filter = request.GET.get('user')
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    # Paginación
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener acciones disponibles
    available_actions = ChangeLog.objects.filter(template=template).values_list('action', flat=True).distinct()
    
    context = {
        'template': template,
        'page_obj': page_obj,
        'available_actions': available_actions,
        'current_action': action_filter,
        'current_user': user_filter
    }
    
    return render(request, 'versions/change_log.html', context)