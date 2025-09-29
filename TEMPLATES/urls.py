from django.urls import path
from . import views

app_name = 'templates'

urlpatterns = [
    # Lista y gestión de plantillas
    path('', views.template_list, name='template_list'),
    path('create/', views.create_template, name='create_template'),
    path('<int:template_id>/', views.template_detail, name='template_detail'),
    path('<int:template_id>/edit/', views.template_editor, name='template_editor'),
    path('<int:template_id>/delete/', views.delete_template, name='delete_template'),
    
    # Operaciones del editor
    path('<int:template_id>/save/', views.save_template, name='save_template'),
    path('<int:template_id>/preview/', views.preview_template, name='preview_template'),
    path('<int:template_id>/export/', views.export_template, name='export_template'),
    
    # Gestión de placeholders
    path('<int:template_id>/placeholders/', views.get_placeholders, name='get_placeholders'),
    path('<int:template_id>/placeholders/add/', views.add_placeholder, name='add_placeholder'),
    path('<int:template_id>/placeholders/<int:placeholder_id>/edit/', views.edit_placeholder, name='edit_placeholder'),
    path('<int:template_id>/placeholders/<int:placeholder_id>/delete/', views.delete_placeholder, name='delete_placeholder'),
    
    # Categorías de plantillas
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<int:category_id>/', views.category_detail, name='category_detail'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    
    # Duplicar y clonar plantillas
    path('<int:template_id>/duplicate/', views.duplicate_template, name='duplicate_template'),
    path('<int:template_id>/clone/', views.clone_template, name='clone_template'),
    
    # Búsqueda y filtros
    path('search/', views.search_templates, name='search_templates'),
    path('filter/', views.filter_templates, name='filter_templates'),
]