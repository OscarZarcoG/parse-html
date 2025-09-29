from django.db import models
from django.conf import settings
import os

class Document(models.Model):
    """
    Modelo para almacenar información de documentos originales subidos
    """
    DOCUMENT_TYPES = [
        ('docx', 'Word Document (.docx)'),
        ('xls', 'Excel Spreadsheet (.xls)'),
        ('xlsx', 'Excel Spreadsheet (.xlsx)'),
        ('pdf', 'PDF Document (.pdf)'),
    ]
    
    STATUS_CHOICES = [
        ('uploaded', 'Subido'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('error', 'Error'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Nombre del documento')
    original_filename = models.CharField(max_length=255, verbose_name='Nombre original del archivo')
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES, verbose_name='Tipo de documento')
    file_path = models.FileField(upload_to='documents/', verbose_name='Archivo')
    file_size = models.PositiveIntegerField(verbose_name='Tamaño del archivo (bytes)')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded', verbose_name='Estado')
    processing_log = models.TextField(blank=True, null=True, verbose_name='Log de procesamiento')
    
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Subido por')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de subida')
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name='Fecha de procesamiento')
    
    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"
    
    def get_file_extension(self):
        return os.path.splitext(self.original_filename)[1].lower()
    
    def is_processed(self):
        return self.status == 'completed'

class ParsedContent(models.Model):
    """
    Modelo para almacenar el contenido parseado de los documentos
    """
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='parsed_content')
    
    # Contenido extraído
    raw_text = models.TextField(verbose_name='Texto extraído')
    structured_data = models.JSONField(default=dict, verbose_name='Datos estructurados')
    
    # Información de estilo
    style_info = models.JSONField(default=dict, verbose_name='Información de estilo')
    fonts_used = models.JSONField(default=list, verbose_name='Fuentes utilizadas')
    colors_used = models.JSONField(default=list, verbose_name='Colores utilizados')
    
    # Placeholders detectados
    placeholders_detected = models.JSONField(default=list, verbose_name='Placeholders detectados')
    red_text_content = models.JSONField(default=list, verbose_name='Contenido en texto rojo')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    
    class Meta:
        verbose_name = 'Contenido Parseado'
        verbose_name_plural = 'Contenidos Parseados'
        
    def __str__(self):
        return f"Contenido parseado de {self.document.name}"
    
    def get_placeholder_count(self):
        return len(self.placeholders_detected)
    
    def has_red_text(self):
        return len(self.red_text_content) > 0
