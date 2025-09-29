from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os
import uuid
from pathlib import Path

from .models import Document, ParsedContent

def truncate_filename(filename, max_length=100):
    """
    Trunca un nombre de archivo para que no exceda max_length caracteres,
    preservando la extensión del archivo.
    """
    if len(filename) <= max_length:
        return filename
    
    # Separar nombre y extensión
    name_part = Path(filename).stem
    extension = Path(filename).suffix
    
    # Calcular cuántos caracteres podemos usar para el nombre
    available_length = max_length - len(extension) - 3  # -3 para "..."
    
    if available_length <= 0:
        # Si la extensión es muy larga, solo usar los primeros caracteres del nombre original
        return filename[:max_length]
    
    # Truncar el nombre y agregar "..." antes de la extensión
    truncated_name = name_part[:available_length] + "..."
    return truncated_name + extension
from .services import document_parser
from TEMPLATES.models import Template, PlaceholderDefinition
from VERSIONS.models import TemplateVersion, Branch, ChangeLog

@login_required
def upload_document(request):
    """
    Vista para subir documentos y mostrar el formulario de subida
    """
    if request.method == 'POST':
        return handle_document_upload(request)
    
    # GET: Mostrar formulario de subida
    recent_documents = Document.objects.filter(uploaded_by=request.user).order_by('-uploaded_at')[:5]
    
    context = {
        'recent_documents': recent_documents,
        'supported_formats': ['.docx', '.xlsx', '.xls', '.pdf'],
        'max_file_size': settings.MAX_UPLOAD_SIZE
    }
    
    return render(request, 'parser/upload_document.html', context)

@login_required
@csrf_exempt
def handle_document_upload(request):
    """
    Maneja la subida de archivos y inicia el proceso de parseo
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    if 'document' not in request.FILES:
        return JsonResponse({'error': 'No se ha seleccionado ningún archivo'}, status=400)
    
    uploaded_file = request.FILES['document']
    
    # Validar tipo de archivo
    file_extension = Path(uploaded_file.name).suffix.lower()
    if file_extension not in ['.docx', '.xlsx', '.xls', '.pdf']:
        return JsonResponse({'error': f'Formato de archivo no soportado: {file_extension}'}, status=400)
    
    # Validar tamaño de archivo
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        return JsonResponse({'error': 'El archivo es demasiado grande'}, status=400)
    
    try:
        # Crear registro del documento
        document = Document.objects.create(
            name=truncate_filename(uploaded_file.name),
            original_filename=uploaded_file.name,
            document_type=file_extension[1:],  # Sin el punto
            file_size=uploaded_file.size,
            uploaded_by=request.user,
            status='uploaded'
        )
        
        # Guardar archivo físico
        file_path = save_uploaded_file(uploaded_file, document.id)
        document.file_path = file_path
        document.status = 'processing'
        document.save()
        
        # Iniciar parseo en segundo plano (o síncronamente para esta demo)
        parse_result = parse_document_sync(document)
        
        if parse_result['success']:
            return JsonResponse({
                'success': True,
                'document_id': document.id,
                'message': 'Documento procesado exitosamente',
                'redirect_url': f'/parser/{document.id}/preview/'
            })
        else:
            document.status = 'error'
            document.processing_log = parse_result.get('error', 'Error desconocido')
            document.save()
            return JsonResponse({'error': parse_result.get('error', 'Error al procesar el documento')}, status=500)
    
    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

def save_uploaded_file(uploaded_file, document_id):
    """
    Guarda el archivo subido en el sistema de archivos usando Django storage
    """
    # Crear ruta relativa para el archivo dentro de uploads
    relative_path = f"uploads/{document_id}/{uploaded_file.name}"
    
    # Usar Django's default storage para guardar el archivo
    file_path = default_storage.save(relative_path, ContentFile(uploaded_file.read()))
    
    # Retornar la ruta completa del archivo
    return default_storage.path(file_path)

def parse_document_sync(document):
    """
    Parsea un documento de forma síncrona
    """
    try:
        # Usar el servicio de parseo
        parse_result = document_parser.parse_document(document.file_path, document.document_type)
        
        if parse_result['success']:
            # Crear registro de contenido parseado
            parsed_content = ParsedContent.objects.create(
                document=document,
                raw_text=json.dumps(parse_result['content']['raw_data']),
                structured_data=parse_result['content']['raw_data'],
                style_info={
                    'html_content': parse_result['content']['html'],
                    'css_content': parse_result['content']['css'],
                    'js_content': parse_result['content']['js']
                },
                placeholders_detected=parse_result['content']['placeholders']
            )
            
            # Crear plantilla automáticamente
            template = create_template_from_parsed_content(document, parsed_content)
            
            # Actualizar estado del documento
            document.status = 'completed'
            document.save()
            
            return {'success': True, 'template_id': template.id}
        else:
            return parse_result
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_template_from_parsed_content(document, parsed_content):
    """
    Crea una plantilla a partir del contenido parseado
    """
    # Crear plantilla con nombre truncado si es necesario
    template_name = f"Plantilla de {document.name}"
    if len(template_name) > 255:  # Template.name tiene max_length=255
        template_name = template_name[:252] + "..."
    
    template = Template.objects.create(
        name=template_name,
        description=f"Plantilla generada automáticamente desde {document.original_filename}",
        source_document=document,
        html_file_path='',  # Se establecerá después
        css_file_path='',   # Se establecerá después
        js_file_path='',    # Se establecerá después
        html_content=parsed_content.style_info.get('html_content', ''),
        css_content=parsed_content.style_info.get('css_content', ''),
        js_content=parsed_content.style_info.get('js_content', ''),
        placeholders=parsed_content.placeholders_detected,
        created_by=document.uploaded_by,
        last_modified_by=document.uploaded_by,
        status='draft'
    )
    
    # Crear primera versión
    first_version = TemplateVersion.objects.create(
        template=template,
        version_number=1,
        branch_name='main',
        html_content=parsed_content.style_info.get('html_content', ''),
        css_content=parsed_content.style_info.get('css_content', ''),
        js_content=parsed_content.style_info.get('js_content', ''),
        commit_message='Versión inicial generada automáticamente',
        changes_summary={'type': 'initial', 'files': ['html', 'css', 'js']},
        author=document.uploaded_by,
        status='committed',
        is_current=True
    )
    
    # Crear rama principal con la versión base
    main_branch = Branch.objects.create(
        template=template,
        name='main',
        description='Rama principal',
        is_main=True,
        created_by=document.uploaded_by,
        base_version=first_version  # Ahora ya tenemos la versión creada
    )
    
    # Crear definiciones de placeholders
    for placeholder in parsed_content.placeholders_detected:
        # Truncar el nombre del placeholder si excede 100 caracteres
        placeholder_name = placeholder['name']
        if len(placeholder_name) > 100:
            placeholder_name = placeholder_name[:97] + "..."
        
        PlaceholderDefinition.objects.create(
            template=template,
            name=placeholder_name,
            placeholder_type=placeholder['type'],
            description=placeholder.get('description', ''),
            default_value=placeholder.get('default_value', ''),
            is_required=placeholder.get('required', False)
        )
    
    # Registrar cambio en el log
    ChangeLog.objects.create(
        template=template,
        version=first_version,
        action='create',
        description=f'Plantilla creada automáticamente desde {document.original_filename}',
        changes_detail={
            'source_document': document.original_filename,
            'placeholders_count': len(parsed_content.placeholders_detected),
            'file_type': document.document_type
        },
        affected_files=['html', 'css', 'js'],
        user=document.uploaded_by
    )
    
    return template

@login_required
def document_detail(request, document_id):
    """
    Vista detallada de un documento procesado
    """
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    try:
        parsed_content = document.parsed_content
        template = Template.objects.filter(source_document=document).first()
    except ParsedContent.DoesNotExist:
        parsed_content = None
        template = None
    
    context = {
        'document': document,
        'parsed_content': parsed_content,
        'template': template,
        'placeholders': parsed_content.placeholders_detected if parsed_content else []
    }
    
    return render(request, 'parser/document_detail.html', context)

@login_required
def document_preview(request, document_id):
    """
    Vista previa del documento parseado
    """
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    try:
        parsed_content = document.parsed_content
        template = Template.objects.filter(source_document=document).first()
    except ParsedContent.DoesNotExist:
        messages.error(request, 'El documento no ha sido procesado correctamente.')
        return redirect('parser:upload_document')
    
    # Datos de prueba para los placeholders
    test_data = generate_test_data_for_placeholders(parsed_content.placeholders_detected)
    
    context = {
        'document': document,
        'parsed_content': parsed_content,
        'template': template,
        'test_data': test_data,
        'html_content': parsed_content.style_info.get('html_content', ''),
        'css_content': parsed_content.style_info.get('css_content', ''),
        'js_content': parsed_content.style_info.get('js_content', '')
    }
    
    return render(request, 'parser/document_preview.html', context)

@login_required
def document_list(request):
    """
    Lista de documentos del usuario
    """
    documents = Document.objects.filter(uploaded_by=request.user).order_by('-uploaded_at')
    
    # Filtros
    status_filter = request.GET.get('status')
    if status_filter:
        documents = documents.filter(status=status_filter)
    
    file_type_filter = request.GET.get('file_type')
    if file_type_filter:
        documents = documents.filter(document_type=file_type_filter)
    
    context = {
        'documents': documents,
        'status_choices': Document.STATUS_CHOICES,
        'file_types': ['docx', 'xlsx', 'xls', 'pdf'],
        'current_status': status_filter,
        'current_file_type': file_type_filter
    }
    
    return render(request, 'parser/document_list.html', context)

@login_required
@require_http_methods(["DELETE"])
def delete_document(request, document_id):
    """
    Elimina un documento y sus archivos asociados
    """
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    try:
        # Eliminar archivos físicos
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Eliminar directorio del documento si está vacío
        document_dir = Path(document.file_path).parent
        if document_dir.exists() and not any(document_dir.iterdir()):
            document_dir.rmdir()
        
        # Eliminar registro de la base de datos
        document_name = document.name
        document.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Documento "{document_name}" eliminado correctamente'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al eliminar el documento: {str(e)}'
        }, status=500)

@login_required
def reprocess_document(request, document_id):
    """
    Reprocesa un documento
    """
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    if request.method == 'POST':
        try:
            # Cambiar estado a procesando
            document.status = 'processing'
            document.processing_log = ''
            document.save()
            
            # Eliminar contenido parseado anterior si existe
            if hasattr(document, 'parsed_content'):
                document.parsed_content.delete()
            
            # Reprocesar
            parse_result = parse_document_sync(document)
            
            if parse_result['success']:
                messages.success(request, 'Documento reprocesado exitosamente')
                return redirect('parser:document_detail', document_id=document.id)
            else:
                messages.error(request, f'Error al reprocesar: {parse_result.get("error", "Error desconocido")}')
        
        except Exception as e:
            messages.error(request, f'Error interno: {str(e)}')
    
    return redirect('parser:document_detail', document_id=document.id)

def generate_test_data_for_placeholders(placeholders_data):
    """
    Genera datos de prueba para los placeholders
    """
    test_data = {}
    
    for placeholder in placeholders_data:
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
    
    return test_data

@login_required
def export_template_files(request, document_id):
    """
    Exporta los archivos HTML, CSS y JS de una plantilla
    """
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    try:
        parsed_content = document.parsed_content
    except ParsedContent.DoesNotExist:
        messages.error(request, 'El documento no ha sido procesado.')
        return redirect('parser:document_detail', document_id=document.id)
    
    # Crear archivos temporales
    import tempfile
    import zipfile
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip, 'w') as zip_file:
                # Agregar HTML
                zip_file.writestr('index.html', parsed_content.style_info.get('html_content', ''))
                # Agregar CSS
                zip_file.writestr('styles.css', parsed_content.style_info.get('css_content', ''))
                # Agregar JS
                zip_file.writestr('script.js', parsed_content.style_info.get('js_content', ''))
                
                # Agregar archivo de información de placeholders
                placeholders_info = json.dumps(parsed_content.placeholders_detected, indent=2, ensure_ascii=False)
                zip_file.writestr('placeholders.json', placeholders_info)
            
            # Leer el archivo zip
            temp_zip.seek(0)
            with open(temp_zip.name, 'rb') as f:
                zip_content = f.read()
            
            # Eliminar archivo temporal
            os.unlink(temp_zip.name)
            
            # Retornar como descarga
            response = HttpResponse(zip_content, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="plantilla_{document.name}.zip"'
            return response
    
    except Exception as e:
        messages.error(request, f'Error al exportar: {str(e)}')
        return redirect('parser:document_detail', document_id=document.id)

@login_required
def edit_document(request, document_id):
    """
    Editar metadatos de un documento
    """
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    
    if request.method == 'POST':
        # Actualizar nombre del documento
        new_name = request.POST.get('name', '').strip()
        if new_name and new_name != document.name:
            document.name = new_name
            document.save()
            messages.success(request, 'Documento actualizado correctamente')
            return redirect('parser:document_list')
    
    context = {
        'document': document
    }
    
    return render(request, 'parser/edit_document.html', context)
