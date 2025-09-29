from django.contrib.auth.models import AbstractUser
from django.db import models

class UserCustom(AbstractUser):
    """
    Modelo de usuario personalizado con roles específicos para el sistema de parseo
    """
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('editor', 'Editor'),
        ('viewer', 'Visualizador'),
    ]
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='viewer',
        verbose_name='Rol'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_editor(self):
        return self.role in ['admin', 'editor']
    
    def can_edit_templates(self):
        return self.role in ['admin', 'editor']
    
    def can_manage_users(self):
        return self.role == 'admin'
