from django.contrib import admin
from .models import Document, ParsedContent

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'document_type', 'status', 'uploaded_by', 'uploaded_at', 'file_size')
    list_filter = ('document_type', 'status', 'uploaded_at')
    search_fields = ('name', 'original_filename', 'uploaded_by__username')
    readonly_fields = ('uploaded_at', 'processed_at', 'file_size')
    ordering = ('-uploaded_at',)
    
    fieldsets = (
        ('Información del Documento', {
            'fields': ('name', 'original_filename', 'document_type', 'file_path')
        }),
        ('Estado y Procesamiento', {
            'fields': ('status', 'processing_log', 'uploaded_by')
        }),
        ('Fechas', {
            'fields': ('uploaded_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ParsedContent)
class ParsedContentAdmin(admin.ModelAdmin):
    list_display = ('document', 'get_placeholder_count', 'has_red_text', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('document__name', 'raw_text')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Documento Asociado', {
            'fields': ('document',)
        }),
        ('Contenido Extraído', {
            'fields': ('raw_text', 'structured_data')
        }),
        ('Información de Estilo', {
            'fields': ('style_info', 'fonts_used', 'colors_used'),
            'classes': ('collapse',)
        }),
        ('Placeholders y Contenido Especial', {
            'fields': ('placeholders_detected', 'red_text_content')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
