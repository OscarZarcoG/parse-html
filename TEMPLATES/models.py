from django.db import models
from django.conf import settings
from PARSER.models import Document
import os

class TemplateCategory(models.Model):
    """
    Categorías para organizar las plantillas
    """
    name = models.CharField(max_length=100, verbose_name='Nombre de la categoría')
    description = models.TextField(blank=True, verbose_name='Descripción')
    color = models.CharField(max_length=7, default='#007bff', verbose_name='Color (hex)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Creado por')
    
    class Meta:
        verbose_name = 'Categoría de Plantilla'
        verbose_name_plural = 'Categorías de Plantillas'
        ordering = ['name']
        
    def __str__(self):
        return self.name

class Template(models.Model):
    """
    Modelo principal para las plantillas HTML generadas
    """
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('archived', 'Archivada'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Nombre de la plantilla')
    description = models.TextField(blank=True, verbose_name='Descripción')
    category = models.ForeignKey(TemplateCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Categoría')
    
    # Relación con el documento original
    source_document = models.ForeignKey(Document, on_delete=models.CASCADE, verbose_name='Documento origen')
    
    # Archivos generados
    html_file_path = models.CharField(max_length=500, verbose_name='Ruta del archivo HTML')
    css_file_path = models.CharField(max_length=500, verbose_name='Ruta del archivo CSS')
    js_file_path = models.CharField(max_length=500, verbose_name='Ruta del archivo JS')
    
    # Contenido de los archivos
    html_content = models.TextField(verbose_name='Contenido HTML')
    css_content = models.TextField(verbose_name='Contenido CSS')
    js_content = models.TextField(blank=True, verbose_name='Contenido JavaScript')
    
    # Metadatos
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Estado')
    tags = models.JSONField(default=list, verbose_name='Etiquetas')
    
    # Placeholders
    placeholders = models.JSONField(default=list, verbose_name='Lista de placeholders')
    placeholder_descriptions = models.JSONField(default=dict, verbose_name='Descripciones de placeholders')
    
    # Información de creación y modificación
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_templates', verbose_name='Creado por')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='modified_templates', verbose_name='Última modificación por')
    
    class Meta:
        verbose_name = 'Plantilla'
        verbose_name_plural = 'Plantillas'
        ordering = ['-updated_at']
        
    def __str__(self):
        return f"{self.name} (v{self.get_current_version()})"
    
    def get_current_version(self):
        """Obtiene el número de la versión actual"""
        from VERSIONS.models import TemplateVersion
        latest_version = self.versions.order_by('-version_number').first()
        return latest_version.version_number if latest_version else 1
    
    def get_placeholder_count(self):
        return len(self.placeholders)
    
    def is_active(self):
        return self.status == 'active'
    
    def get_file_paths(self):
        return {
            'html': self.html_file_path,
            'css': self.css_file_path,
            'js': self.js_file_path
        }

class TemplatePreview(models.Model):
    """
    Modelo para almacenar vistas previas de plantillas con datos de prueba
    """
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='previews', verbose_name='Plantilla')
    name = models.CharField(max_length=100, verbose_name='Nombre de la vista previa')
    
    # Datos de prueba para los placeholders
    test_data = models.JSONField(default=dict, verbose_name='Datos de prueba')
    
    # HTML renderizado con los datos de prueba
    rendered_html = models.TextField(verbose_name='HTML renderizado')
    
    # Configuración de vista previa
    viewport_width = models.PositiveIntegerField(default=1200, verbose_name='Ancho de viewport')
    viewport_height = models.PositiveIntegerField(default=800, verbose_name='Alto de viewport')
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Creado por')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    
    class Meta:
        verbose_name = 'Vista Previa de Plantilla'
        verbose_name_plural = 'Vistas Previas de Plantillas'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Vista previa: {self.name} - {self.template.name}"

class PlaceholderDefinition(models.Model):
    """
    Definiciones detalladas de placeholders para las plantillas
    """
    PLACEHOLDER_TYPES = [
        ('text', 'Texto'),
        ('number', 'Número'),
        ('date', 'Fecha'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('image', 'Imagen'),
        ('boolean', 'Booleano'),
        ('list', 'Lista'),
    ]
    
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='placeholder_definitions', verbose_name='Plantilla')
    
    name = models.CharField(max_length=100, verbose_name='Nombre del placeholder')
    display_name = models.CharField(max_length=150, verbose_name='Nombre para mostrar')
    description = models.TextField(blank=True, verbose_name='Descripción')
    
    placeholder_type = models.CharField(max_length=20, choices=PLACEHOLDER_TYPES, default='text', verbose_name='Tipo de placeholder')
    is_required = models.BooleanField(default=False, verbose_name='Es requerido')
    default_value = models.TextField(blank=True, verbose_name='Valor por defecto')
    
    # Validaciones
    max_length = models.PositiveIntegerField(null=True, blank=True, verbose_name='Longitud máxima')
    min_length = models.PositiveIntegerField(null=True, blank=True, verbose_name='Longitud mínima')
    validation_regex = models.CharField(max_length=500, blank=True, verbose_name='Expresión regular de validación')
    
    # Posición en el documento
    position_info = models.JSONField(default=dict, verbose_name='Información de posición')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    
    class Meta:
        verbose_name = 'Definición de Placeholder'
        verbose_name_plural = 'Definiciones de Placeholders'
        unique_together = ['template', 'name']
        ordering = ['name']
        
    def __str__(self):
        return f"{self.template.name} - {self.display_name}"
