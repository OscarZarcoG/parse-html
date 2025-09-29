from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import models
import json
import os
import uuid
from pathlib import Path

from .models import Template, PlaceholderDefinition, TemplateCategory
from VERSIONS.models import TemplateVersion, Branch, ChangeLog
from PARSER.models import Document

@login_required
def template_list(request):
    """
    Lista de plantillas del usuario
    """
    templates = Template.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Filtros
    status_filter = request.GET.get('status')
    if status_filter:
        templates = templates.filter(status=status_filter)
    
    category_filter = request.GET.get('category')
    if category_filter:
        templates = templates.filter(category_id=category_filter)
    
    # Paginación
    paginator = Paginator(templates, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Categorías para el filtro
    categories = TemplateCategory.objects.all()
    
    context = {
        'page_obj': page_obj,
        'templates': page_obj,
        'categories': categories,
        'status_choices': Template.STATUS_CHOICES,
        'current_status': status_filter,
        'current_category': category_filter
    }
    
    return render(request, 'templates/template_list.html', context)

@login_required
def create_template(request):
    """
    Crear nueva plantilla
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category_id = request.POST.get('category')
        
        if not name:
            messages.error(request, 'El nombre de la plantilla es requerido.')
            return redirect('templates:create_template')
        
        try:
            # Crear plantilla
            template = Template.objects.create(
                name=name,
                description=description,
                category_id=category_id if category_id else None,
                html_content='<!DOCTYPE html>\n<html>\n<head>\n    <title>Nueva Plantilla</title>\n    <link rel="stylesheet" href="styles.css">\n</head>\n<body>\n    <h1>{{titulo}}</h1>\n    <p>{{contenido}}</p>\n    <script src="script.js"></script>\n</body>\n</html>',
                css_content='body {\n    font-family: Arial, sans-serif;\n    margin: 20px;\n    line-height: 1.6;\n}\n\nh1 {\n    color: #333;\n    border-bottom: 2px solid #007bff;\n    padding-bottom: 10px;\n}\n\np {\n    color: #666;\n    margin: 15px 0;\n}',
                js_content='// JavaScript para la plantilla\nconsole.log("Plantilla cargada");',
                placeholders_data=[
                    {'name': 'titulo', 'type': 'text', 'description': 'Título principal'},
                    {'name': 'contenido', 'type': 'text', 'description': 'Contenido principal'}
                ],
                created_by=request.user,
                status='draft'
            )
            
            # Crear rama principal
            main_branch = Branch.objects.create(
                template=template,
                name='main',
                description='Rama principal',
                is_main=True,
                created_by=request.user
            )
            
            # Crear primera versión
            first_version = TemplateVersion.objects.create(
                template=template,
                version_number=1,
                branch_name='main',
                html_content=template.html_content,
                css_content=template.css_content,
                js_content=template.js_content,
                commit_message='Versión inicial',
                changes_summary={'type': 'initial', 'files': ['html', 'css', 'js']},
                author=request.user,
                status='committed',
                is_current=True
            )
            
            # Actualizar rama con versión base
            main_branch.base_version = first_version
            main_branch.save()
            
            # Crear placeholders
            for placeholder in template.placeholders_data:
                PlaceholderDefinition.objects.create(
                    template=template,
                    name=placeholder['name'],
                    placeholder_type=placeholder['type'],
                    description=placeholder.get('description', ''),
                    is_required=True
                )
            
            # Registrar en el log
            ChangeLog.objects.create(
                template=template,
                version=first_version,
                action='create',
                description=f'Plantilla "{name}" creada manualmente',
                changes_detail={'type': 'manual_creation'},
                affected_files=['html', 'css', 'js'],
                user=request.user
            )
            
            messages.success(request, f'Plantilla "{name}" creada exitosamente.')
            return redirect('templates:template_detail', template_id=template.id)
        
        except Exception as e:
            messages.error(request, f'Error al crear la plantilla: {str(e)}')
    
    # GET: Mostrar formulario
    categories = TemplateCategory.objects.all()
    context = {
        'categories': categories
    }
    
    return render(request, 'templates/create_template.html', context)

@login_required
def template_detail(request, template_id):
    """
    Vista detallada de una plantilla
    """
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    
    # Obtener versiones recientes
    recent_versions = TemplateVersion.objects.filter(template=template).order_by('-created_at')[:5]
    
    # Obtener placeholders
    placeholders = PlaceholderDefinition.objects.filter(template=template)
    
    # Obtener ramas
    branches = Branch.objects.filter(template=template)
    
    # Estadísticas
    stats = {
        'total_versions': TemplateVersion.objects.filter(template=template).count(),
        'total_branches': branches.count(),
        'total_placeholders': placeholders.count(),
        'current_version': template.current_version_number if hasattr(template, 'current_version_number') else 1
    }
    
    context = {
        'template': template,
        'recent_versions': recent_versions,
        'placeholders': placeholders,
        'branches': branches,
        'stats': stats
    }
    
    return render(request, 'templates/template_detail.html', context)

@login_required
def template_editor(request, template_id):
    """
    Editor de plantillas
    """
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    placeholders = PlaceholderDefinition.objects.filter(template=template)
    
    context = {
        'template': template,
        'placeholders': placeholders,
        'html_content': template.html_content,
        'css_content': template.css_content,
        'js_content': template.js_content
    }
    
    return render(request, 'templates/template_editor.html', context)

@login_required
@csrf_exempt
def save_template(request, template_id):
    """
    Guardar cambios en la plantilla
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        
        html_content = data.get('html_content', template.html_content)
        css_content = data.get('css_content', template.css_content)
        js_content = data.get('js_content', template.js_content)
        commit_message = data.get('commit_message', 'Cambios guardados automáticamente')
        
        # Verificar si hay cambios
        has_changes = (
            html_content != template.html_content or
            css_content != template.css_content or
            js_content != template.js_content
        )
        
        if not has_changes:
            return JsonResponse({'success': True, 'message': 'No hay cambios para guardar'})
        
        # Actualizar plantilla
        template.html_content = html_content
        template.css_content = css_content
        template.js_content = js_content
        template.updated_at = timezone.now()
        template.save()
        
        # Crear nueva versión
        last_version = TemplateVersion.objects.filter(template=template).order_by('-version_number').first()
        new_version_number = (last_version.version_number + 1) if last_version else 1
        
        new_version = TemplateVersion.objects.create(
            template=template,
            version_number=new_version_number,
            branch_name='main',
            html_content=html_content,
            css_content=css_content,
            js_content=js_content,
            commit_message=commit_message,
            changes_summary={'type': 'edit', 'files': ['html', 'css', 'js']},
            author=request.user,
            status='committed',
            is_current=True
        )
        
        # Marcar versiones anteriores como no actuales
        TemplateVersion.objects.filter(template=template, is_current=True).exclude(id=new_version.id).update(is_current=False)
        
        # Registrar cambio
        ChangeLog.objects.create(
            template=template,
            version=new_version,
            action='edit',
            description=commit_message,
            changes_detail={'version': new_version_number},
            affected_files=['html', 'css', 'js'],
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Plantilla guardada exitosamente',
            'version_number': new_version_number
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Error al guardar: {str(e)}'}, status=500)

@login_required
def preview_template(request, template_id):
    """
    Vista previa de la plantilla
    """
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    
    # Generar datos de prueba para placeholders
    test_data = {}
    for placeholder in template.placeholders_data:
        name = placeholder['name']
        placeholder_type = placeholder['type']
        
        if placeholder_type == 'date':
            test_data[name] = '2024-01-15'
        elif placeholder_type == 'number':
            test_data[name] = '1234'
        elif placeholder_type == 'email':
            test_data[name] = 'ejemplo@correo.com'
        elif placeholder_type == 'phone':
            test_data[name] = '+52 55 1234 5678'
        else:  # text
            test_data[name] = f'Texto de ejemplo para {name}'
    
    context = {
        'template': template,
        'test_data': test_data,
        'html_content': template.html_content,
        'css_content': template.css_content,
        'js_content': template.js_content
    }
    
    return render(request, 'templates/template_preview.html', context)

@login_required
def export_template(request, template_id):
    """
    Exportar plantilla como archivo ZIP
    """
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    
    import tempfile
    import zipfile
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip, 'w') as zip_file:
                # Agregar archivos
                zip_file.writestr('index.html', template.html_content)
                zip_file.writestr('styles.css', template.css_content)
                zip_file.writestr('script.js', template.js_content)
                
                # Agregar información de placeholders
                placeholders_info = json.dumps(template.placeholders_data, indent=2, ensure_ascii=False)
                zip_file.writestr('placeholders.json', placeholders_info)
                
                # Agregar README
                readme_content = f"""# {template.name}

{template.description}

## Placeholders disponibles:
"""
                for placeholder in template.placeholders_data:
                    readme_content += f"- {{{{ {placeholder['name']} }}}}: {placeholder.get('description', 'Sin descripción')}\n"
                
                zip_file.writestr('README.md', readme_content)
            
            # Leer archivo
            temp_zip.seek(0)
            with open(temp_zip.name, 'rb') as f:
                zip_content = f.read()
            
            # Eliminar archivo temporal
            os.unlink(temp_zip.name)
            
            # Retornar descarga
            response = HttpResponse(zip_content, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{template.name}.zip"'
            return response
    
    except Exception as e:
        messages.error(request, f'Error al exportar: {str(e)}')
        return redirect('templates:template_detail', template_id=template.id)

@login_required
@require_http_methods(["DELETE"])
def delete_template(request, template_id):
    """
    Eliminar plantilla
    """
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    
    try:
        template_name = template.name
        template.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Plantilla "{template_name}" eliminada correctamente'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al eliminar: {str(e)}'
        }, status=500)

@login_required
def get_placeholders(request, template_id):
    """
    Obtener placeholders de una plantilla
    """
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    placeholders = PlaceholderDefinition.objects.filter(template=template)
    
    data = []
    for placeholder in placeholders:
        data.append({
            'id': placeholder.id,
            'name': placeholder.name,
            'type': placeholder.placeholder_type,
            'description': placeholder.description,
            'default_value': placeholder.default_value,
            'is_required': placeholder.is_required
        })
    
    return JsonResponse({'placeholders': data})

@login_required
@csrf_exempt
def add_placeholder(request, template_id):
    """
    Agregar nuevo placeholder
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    
    try:
        data = json.loads(request.body)
        
        placeholder = PlaceholderDefinition.objects.create(
            template=template,
            name=data['name'],
            placeholder_type=data['type'],
            description=data.get('description', ''),
            default_value=data.get('default_value', ''),
            is_required=data.get('is_required', False)
        )
        
        # Actualizar placeholders_data en la plantilla
        template.placeholders_data.append({
            'name': placeholder.name,
            'type': placeholder.placeholder_type,
            'description': placeholder.description,
            'default_value': placeholder.default_value,
            'required': placeholder.is_required
        })
        template.save()
        
        return JsonResponse({
            'success': True,
            'placeholder': {
                'id': placeholder.id,
                'name': placeholder.name,
                'type': placeholder.placeholder_type,
                'description': placeholder.description,
                'default_value': placeholder.default_value,
                'is_required': placeholder.is_required
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Error al agregar placeholder: {str(e)}'}, status=500)

@login_required
@csrf_exempt
def edit_placeholder(request, template_id, placeholder_id):
    """
    Editar placeholder existente
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    placeholder = get_object_or_404(PlaceholderDefinition, id=placeholder_id, template=template)
    
    try:
        data = json.loads(request.body)
        
        placeholder.name = data.get('name', placeholder.name)
        placeholder.placeholder_type = data.get('type', placeholder.placeholder_type)
        placeholder.description = data.get('description', placeholder.description)
        placeholder.default_value = data.get('default_value', placeholder.default_value)
        placeholder.is_required = data.get('is_required', placeholder.is_required)
        placeholder.save()
        
        # Actualizar placeholders_data en la plantilla
        for i, p in enumerate(template.placeholders_data):
            if p['name'] == placeholder.name:
                template.placeholders_data[i] = {
                    'name': placeholder.name,
                    'type': placeholder.placeholder_type,
                    'description': placeholder.description,
                    'default_value': placeholder.default_value,
                    'required': placeholder.is_required
                }
                break
        template.save()
        
        return JsonResponse({
            'success': True,
            'placeholder': {
                'id': placeholder.id,
                'name': placeholder.name,
                'type': placeholder.placeholder_type,
                'description': placeholder.description,
                'default_value': placeholder.default_value,
                'is_required': placeholder.is_required
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': f'Error al editar placeholder: {str(e)}'}, status=500)

@login_required
@require_http_methods(["DELETE"])
def delete_placeholder(request, template_id, placeholder_id):
    """
    Eliminar placeholder
    """
    template = get_object_or_404(Template, id=template_id, created_by=request.user)
    placeholder = get_object_or_404(PlaceholderDefinition, id=placeholder_id, template=template)
    
    try:
        placeholder_name = placeholder.name
        placeholder.delete()
        
        # Actualizar placeholders_data en la plantilla
        template.placeholders_data = [p for p in template.placeholders_data if p['name'] != placeholder_name]
        template.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Placeholder "{placeholder_name}" eliminado correctamente'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al eliminar: {str(e)}'
        }, status=500)

@login_required
def duplicate_template(request, template_id):
    """
    Duplicar plantilla
    """
    original_template = get_object_or_404(Template, id=template_id, created_by=request.user)
    
    try:
        # Crear copia
        new_template = Template.objects.create(
            name=f"{original_template.name} (Copia)",
            description=f"Copia de: {original_template.description}",
            category=original_template.category,
            html_content=original_template.html_content,
            css_content=original_template.css_content,
            js_content=original_template.js_content,
            placeholders_data=original_template.placeholders_data.copy(),
            created_by=request.user,
            status='draft'
        )
        
        # Copiar placeholders
        for placeholder in PlaceholderDefinition.objects.filter(template=original_template):
            PlaceholderDefinition.objects.create(
                template=new_template,
                name=placeholder.name,
                placeholder_type=placeholder.placeholder_type,
                description=placeholder.description,
                default_value=placeholder.default_value,
                is_required=placeholder.is_required
            )
        
        messages.success(request, f'Plantilla duplicada como "{new_template.name}"')
        return redirect('templates:template_detail', template_id=new_template.id)
    
    except Exception as e:
        messages.error(request, f'Error al duplicar: {str(e)}')
        return redirect('templates:template_detail', template_id=template_id)

# Alias para clone_template
clone_template = duplicate_template

@login_required
def search_templates(request):
    """
    Buscar plantillas
    """
    query = request.GET.get('q', '')
    templates = Template.objects.filter(created_by=request.user)
    
    if query:
        templates = templates.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query)
        )
    
    context = {
        'templates': templates,
        'query': query
    }
    
    return render(request, 'templates/search_results.html', context)

@login_required
def filter_templates(request):
    """
    Filtrar plantillas
    """
    return redirect('templates:template_list')

# Vistas para categorías
@login_required
def category_list(request):
    """
    Lista de categorías
    """
    categories = TemplateCategory.objects.all()
    return render(request, 'templates/category_list.html', {'categories': categories})

@login_required
def create_category(request):
    """
    Crear categoría
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if name:
            TemplateCategory.objects.create(name=name, description=description)
            messages.success(request, f'Categoría "{name}" creada exitosamente.')
        else:
            messages.error(request, 'El nombre es requerido.')
    
    return redirect('templates:category_list')

@login_required
def category_detail(request, category_id):
    """
    Detalle de categoría
    """
    category = get_object_or_404(TemplateCategory, id=category_id)
    templates = Template.objects.filter(category=category, created_by=request.user)
    
    context = {
        'category': category,
        'templates': templates
    }
    
    return render(request, 'templates/category_detail.html', context)

@login_required
def edit_category(request, category_id):
    """
    Editar categoría
    """
    category = get_object_or_404(TemplateCategory, id=category_id)
    
    if request.method == 'POST':
        category.name = request.POST.get('name', category.name)
        category.description = request.POST.get('description', category.description)
        category.save()
        messages.success(request, 'Categoría actualizada exitosamente.')
    
    return redirect('templates:category_detail', category_id=category.id)

@login_required
@require_http_methods(["DELETE"])
def delete_category(request, category_id):
    """
    Eliminar categoría
    """
    category = get_object_or_404(TemplateCategory, id=category_id)
    
    try:
        category_name = category.name
        category.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Categoría "{category_name}" eliminada correctamente'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al eliminar: {str(e)}'
        }, status=500)