from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import os

from .models import UserCustom
from PARSER.models import Document
from TEMPLATES.models import Template, TemplateCategory


def user_login(request):
    """Vista de inicio de sesión"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido, {user.get_full_name() or user.username}!')
                
                # Redirigir a la página solicitada o al dashboard
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Credenciales incorrectas. Por favor verifica tu usuario y contraseña.')
        else:
            messages.error(request, 'Por favor completa todos los campos.')
    
    return render(request, 'auth/login.html')


@login_required
def user_logout(request):
    """Vista de cierre de sesión"""
    user_name = request.user.get_full_name() or request.user.username
    logout(request)
    return redirect('home')


@login_required
def user_profile(request):
    """Vista del perfil de usuario"""
    user = request.user
    
    if request.method == 'POST':
        # Actualizar información del perfil
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        
        # Cambiar contraseña si se proporciona
        new_password = request.POST.get('new_password')
        if new_password:
            current_password = request.POST.get('current_password')
            if user.check_password(current_password):
                user.set_password(new_password)
                messages.success(request, 'Contraseña actualizada correctamente.')
            else:
                messages.error(request, 'La contraseña actual es incorrecta.')
                return render(request, 'auth/profile.html', {'user': user})
        
        user.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        
        # Re-autenticar si se cambió la contraseña
        if new_password:
            user = authenticate(request, username=user.username, password=new_password)
            if user:
                login(request, user)
    
    # Estadísticas del usuario
    user_stats = {
        'total_documents': Document.objects.filter(uploaded_by=user).count(),
        'total_templates': Template.objects.filter(created_by=user).count(),
        'documents_this_month': Document.objects.filter(
            uploaded_by=user,
            uploaded_at__gte=timezone.now() - timedelta(days=30)
        ).count(),
        'storage_used': sum(
            doc.file_size or 0 
            for doc in Document.objects.filter(uploaded_by=user)
        ),
    }
    
    context = {
        'user': user,
        'user_stats': user_stats,
    }
    
    return render(request, 'auth/profile.html', context)


def register(request):
    """Vista de registro de usuario"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        
        # Validaciones
        if not all([username, email, password, password_confirm]):
            messages.error(request, 'Por favor completa todos los campos obligatorios.')
            return render(request, 'auth/register.html')
        
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'auth/register.html')
        
        if len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return render(request, 'auth/register.html')
        
        # Verificar si el usuario ya existe
        if UserCustom.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return render(request, 'auth/register.html')
        
        if UserCustom.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return render(request, 'auth/register.html')
        
        try:
            # Crear usuario
            user = UserCustom.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='viewer'  # Rol por defecto
            )
            
            messages.success(request, 'Cuenta creada exitosamente. ¡Ya puedes iniciar sesión!')
            return redirect('auth:login')
            
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
    
    return render(request, 'auth/register.html')


@login_required
def admin_dashboard(request):
    """Dashboard administrativo (solo para administradores)"""
    if not request.user.is_admin():
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')
    
    # Estadísticas generales del sistema
    total_users = UserCustom.objects.count()
    total_documents = Document.objects.count()
    total_templates = Template.objects.count()
    
    # Usuarios por rol
    users_by_role = UserCustom.objects.values('role').annotate(count=Count('role'))
    
    # Documentos por estado
    documents_by_status = Document.objects.values('status').annotate(count=Count('status'))
    
    # Actividad reciente
    recent_users = UserCustom.objects.order_by('-date_joined')[:10]
    recent_documents = Document.objects.order_by('-uploaded_at')[:10]
    
    # Uso de almacenamiento
    total_storage = sum(doc.file_size or 0 for doc in Document.objects.all())
    
    context = {
        'total_users': total_users,
        'total_documents': total_documents,
        'total_templates': total_templates,
        'users_by_role': users_by_role,
        'documents_by_status': documents_by_status,
        'recent_users': recent_users,
        'recent_documents': recent_documents,
        'total_storage': total_storage,
    }
    
    return render(request, 'admin/dashboard.html', context)
