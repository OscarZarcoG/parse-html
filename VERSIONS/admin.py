from django.contrib import admin
from .models import TemplateVersion, Branch, MergeRequest, ChangeLog

@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    list_display = ('template', 'version_number', 'branch_name', 'status', 'author', 'created_at', 'is_current')
    list_filter = ('status', 'branch_name', 'is_current', 'created_at', 'template__category')
    search_fields = ('template__name', 'commit_message', 'commit_hash', 'author__username')
    readonly_fields = ('commit_hash', 'created_at', 'version_number')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Información de Versión', {
            'fields': ('template', 'version_number', 'branch_name', 'commit_hash', 'status', 'is_current')
        }),
        ('Contenido', {
            'fields': ('html_content', 'css_content', 'js_content'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('commit_message', 'changes_summary', 'parent_version')
        }),
        ('Autoría', {
            'fields': ('author', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'is_main', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_main', 'is_active', 'created_at', 'template__category')
    search_fields = ('name', 'description', 'template__name', 'created_by__username')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('template', 'name', 'description')
        }),
        ('Configuración', {
            'fields': ('base_branch', 'base_version', 'is_active', 'is_main')
        }),
        ('Metadatos', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(MergeRequest)
class MergeRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'template', 'source_branch', 'target_branch', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at', 'template__category')
    search_fields = ('title', 'description', 'template__name', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'merged_at')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('template', 'title', 'description', 'status')
        }),
        ('Ramas y Versiones', {
            'fields': ('source_branch', 'target_branch', 'source_version', 'target_version')
        }),
        ('Conflictos', {
            'fields': ('conflicts',),
            'classes': ('collapse',)
        }),
        ('Revisión', {
            'fields': ('created_by', 'reviewed_by', 'created_at', 'updated_at', 'merged_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ('template', 'action', 'user', 'timestamp', 'get_short_description')
    list_filter = ('action', 'timestamp', 'template__category')
    search_fields = ('template__name', 'description', 'user__username')
    readonly_fields = ('timestamp',)
    
    def get_short_description(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    get_short_description.short_description = 'Descripción'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('template', 'version', 'action', 'description')
        }),
        ('Detalles de Cambios', {
            'fields': ('changes_detail', 'affected_files'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('user', 'timestamp', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
