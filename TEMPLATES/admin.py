from django.contrib import admin
from .models import TemplateCategory, Template, TemplatePreview, PlaceholderDefinition

@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color', 'created_by', 'created_at')
    list_filter = ('created_at', 'created_by')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'status', 'created_by', 'created_at', 'get_placeholder_count')
    list_filter = ('status', 'category', 'created_at', 'created_by')
    search_fields = ('name', 'description', 'tags')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ()
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'category', 'status', 'tags')
        }),
        ('Documento Origen', {
            'fields': ('source_document',)
        }),
        ('Archivos', {
            'fields': ('html_file_path', 'css_file_path', 'js_file_path'),
            'classes': ('collapse',)
        }),
        ('Contenido', {
            'fields': ('html_content', 'css_content', 'js_content'),
            'classes': ('collapse',)
        }),
        ('Placeholders', {
            'fields': ('placeholders', 'placeholder_descriptions'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('created_by', 'last_modified_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TemplatePreview)
class TemplatePreviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'viewport_width', 'viewport_height', 'created_by', 'created_at')
    list_filter = ('created_at', 'template__category')
    search_fields = ('name', 'template__name')
    readonly_fields = ('created_at',)

@admin.register(PlaceholderDefinition)
class PlaceholderDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'template', 'placeholder_type', 'is_required')
    list_filter = ('placeholder_type', 'is_required', 'template__category')
    search_fields = ('name', 'display_name', 'description', 'template__name')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('template', 'name', 'display_name', 'description')
        }),
        ('Configuración', {
            'fields': ('placeholder_type', 'is_required', 'default_value')
        }),
        ('Validación', {
            'fields': ('max_length', 'min_length', 'validation_regex'),
            'classes': ('collapse',)
        }),
        ('Posición', {
            'fields': ('position_info',),
            'classes': ('collapse',)
        }),
    )
