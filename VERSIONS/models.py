from django.db import models
from django.conf import settings
from TEMPLATES.models import Template
import json

class TemplateVersion(models.Model):
    """
    Modelo para el control de versiones de plantillas (similar a Git)
    """
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('committed', 'Confirmado'),
        ('merged', 'Fusionado'),
        ('rollback', 'Rollback'),
    ]
    
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='versions', verbose_name='Plantilla')
    
    # Información de versión
    version_number = models.PositiveIntegerField(verbose_name='Número de versión')
    branch_name = models.CharField(max_length=100, default='main', verbose_name='Nombre de la rama')
    commit_hash = models.CharField(max_length=40, unique=True, verbose_name='Hash del commit')
    
    # Contenido de la versión
    html_content = models.TextField(verbose_name='Contenido HTML')
    css_content = models.TextField(verbose_name='Contenido CSS')
    js_content = models.TextField(blank=True, verbose_name='Contenido JavaScript')
    
    # Metadatos de la versión
    commit_message = models.TextField(verbose_name='Mensaje del commit')
    changes_summary = models.JSONField(default=dict, verbose_name='Resumen de cambios')
    
    # Información del autor
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='authored_versions', verbose_name='Autor')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    
    # Relaciones con otras versiones
    parent_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_versions', verbose_name='Versión padre')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Estado')
    is_current = models.BooleanField(default=False, verbose_name='Es la versión actual')
    
    class Meta:
        verbose_name = 'Versión de Plantilla'
        verbose_name_plural = 'Versiones de Plantillas'
        ordering = ['-version_number']
        unique_together = ['template', 'version_number', 'branch_name']
        
    def __str__(self):
        return f"{self.template.name} v{self.version_number} ({self.branch_name})"
    
    def save(self, *args, **kwargs):
        # Generar hash del commit si no existe
        if not self.commit_hash:
            import hashlib
            import time
            content = f"{self.html_content}{self.css_content}{self.js_content}{time.time()}"
            self.commit_hash = hashlib.sha1(content.encode()).hexdigest()
        
        # Si es la versión actual, desmarcar las demás
        if self.is_current:
            TemplateVersion.objects.filter(template=self.template, is_current=True).update(is_current=False)
        
        super().save(*args, **kwargs)
    
    def get_changes_from_parent(self):
        """Obtiene los cambios respecto a la versión padre"""
        if not self.parent_version:
            return {"type": "initial", "changes": []}
        
        changes = []
        
        # Comparar HTML
        if self.html_content != self.parent_version.html_content:
            changes.append({
                "file": "html",
                "type": "modified",
                "lines_added": self.html_content.count('\n') - self.parent_version.html_content.count('\n')
            })
        
        # Comparar CSS
        if self.css_content != self.parent_version.css_content:
            changes.append({
                "file": "css",
                "type": "modified",
                "lines_added": self.css_content.count('\n') - self.parent_version.css_content.count('\n')
            })
        
        # Comparar JS
        if self.js_content != self.parent_version.js_content:
            changes.append({
                "file": "js",
                "type": "modified",
                "lines_added": self.js_content.count('\n') - self.parent_version.js_content.count('\n')
            })
        
        return {"type": "update", "changes": changes}

class Branch(models.Model):
    """
    Modelo para manejar ramas de desarrollo de plantillas
    """
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='branches', verbose_name='Plantilla')
    
    name = models.CharField(max_length=100, verbose_name='Nombre de la rama')
    description = models.TextField(blank=True, verbose_name='Descripción')
    
    # Rama base
    base_branch = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Rama base')
    base_version = models.ForeignKey(TemplateVersion, on_delete=models.CASCADE, verbose_name='Versión base')
    
    # Estado de la rama
    is_active = models.BooleanField(default=True, verbose_name='Está activa')
    is_main = models.BooleanField(default=False, verbose_name='Es la rama principal')
    
    # Información del creador
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Creado por')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    
    class Meta:
        verbose_name = 'Rama'
        verbose_name_plural = 'Ramas'
        unique_together = ['template', 'name']
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.template.name} - {self.name}"
    
    def get_latest_version(self):
        """Obtiene la última versión de esta rama"""
        return self.template.versions.filter(branch_name=self.name).order_by('-version_number').first()
    
    def get_version_count(self):
        """Obtiene el número de versiones en esta rama"""
        return self.template.versions.filter(branch_name=self.name).count()

class MergeRequest(models.Model):
    """
    Modelo para solicitudes de fusión entre ramas
    """
    STATUS_CHOICES = [
        ('open', 'Abierta'),
        ('approved', 'Aprobada'),
        ('merged', 'Fusionada'),
        ('closed', 'Cerrada'),
        ('rejected', 'Rechazada'),
    ]
    
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='merge_requests', verbose_name='Plantilla')
    
    title = models.CharField(max_length=200, verbose_name='Título')
    description = models.TextField(verbose_name='Descripción')
    
    # Ramas involucradas
    source_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='outgoing_merges', verbose_name='Rama origen')
    target_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='incoming_merges', verbose_name='Rama destino')
    
    # Versiones específicas
    source_version = models.ForeignKey(TemplateVersion, on_delete=models.CASCADE, related_name='source_merges', verbose_name='Versión origen')
    target_version = models.ForeignKey(TemplateVersion, on_delete=models.CASCADE, related_name='target_merges', verbose_name='Versión destino')
    
    # Estado y metadatos
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name='Estado')
    conflicts = models.JSONField(default=list, verbose_name='Conflictos detectados')
    
    # Información del creador y revisor
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_merge_requests', verbose_name='Creado por')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_merge_requests', verbose_name='Revisado por')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    merged_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de fusión')
    
    class Meta:
        verbose_name = 'Solicitud de Fusión'
        verbose_name_plural = 'Solicitudes de Fusión'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} ({self.source_branch.name} → {self.target_branch.name})"
    
    def can_be_merged(self):
        """Verifica si la solicitud puede ser fusionada automáticamente"""
        return len(self.conflicts) == 0 and self.status == 'approved'
    
    def detect_conflicts(self):
        """Detecta conflictos entre las versiones"""
        conflicts = []
        
        # Comparar contenido HTML
        if (self.source_version.html_content != self.target_version.html_content and 
            self.source_version.parent_version and 
            self.source_version.parent_version.html_content != self.target_version.html_content):
            conflicts.append({
                "file": "html",
                "type": "content_conflict",
                "description": "Cambios conflictivos en el contenido HTML"
            })
        
        # Comparar contenido CSS
        if (self.source_version.css_content != self.target_version.css_content and 
            self.source_version.parent_version and 
            self.source_version.parent_version.css_content != self.target_version.css_content):
            conflicts.append({
                "file": "css",
                "type": "content_conflict",
                "description": "Cambios conflictivos en el contenido CSS"
            })
        
        self.conflicts = conflicts
        self.save()
        return conflicts

class ChangeLog(models.Model):
    """
    Registro detallado de cambios para auditoría
    """
    ACTION_CHOICES = [
        ('create', 'Crear'),
        ('update', 'Actualizar'),
        ('delete', 'Eliminar'),
        ('rollback', 'Rollback'),
        ('merge', 'Fusionar'),
        ('branch', 'Crear rama'),
    ]
    
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='change_logs', verbose_name='Plantilla')
    version = models.ForeignKey(TemplateVersion, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Versión')
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Acción')
    description = models.TextField(verbose_name='Descripción del cambio')
    
    # Detalles del cambio
    changes_detail = models.JSONField(default=dict, verbose_name='Detalle de cambios')
    affected_files = models.JSONField(default=list, verbose_name='Archivos afectados')
    
    # Información del usuario
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Usuario')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Fecha y hora')
    
    # Metadatos adicionales
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='Dirección IP')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    
    class Meta:
        verbose_name = 'Registro de Cambios'
        verbose_name_plural = 'Registros de Cambios'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.get_action_display()} - {self.template.name} por {self.user.username}"
