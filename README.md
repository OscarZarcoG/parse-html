# ParseDoc System

[![Django](https://img.shields.io/badge/Django-4.2.7-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-336791?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 📋 Descripción

ParseDoc System es una aplicación web desarrollada en Django que permite el procesamiento y parseo inteligente de documentos en múltiples formatos. El sistema extrae contenido, detecta placeholders, analiza estilos y genera plantillas HTML/CSS/JS reutilizables con un sistema completo de control de versiones.

### ✨ Características Principales

- **🔄 Procesamiento Multi-formato**: Soporte para documentos DOCX, XLS, XLSX y PDF
- **🎨 Extracción de Estilos**: Análisis automático de fuentes, colores y formato
- **📝 Detección de Placeholders**: Identificación inteligente de campos variables
- **🌐 Generación de Plantillas**: Conversión automática a HTML/CSS/JS
- **📊 Control de Versiones**: Sistema completo de versionado con ramas y historial
- **👥 Gestión de Usuarios**: Roles diferenciados (Admin, Editor, Visualizador)
- **🔐 Autenticación Segura**: Sistema de login con validación en tiempo real
- **📱 Interfaz Responsiva**: Diseño moderno con Bootstrap 5
- **🚀 API REST**: Endpoints para integración con otros sistemas

## 🛠️ Stack Tecnológico

### Backend
- **Framework**: Django 4.2.7
- **Base de Datos**: PostgreSQL
- **API**: Django REST Framework
- **Autenticación**: Token-based Authentication

### Frontend
- **CSS Framework**: Bootstrap 5.3.0
- **Iconos**: Font Awesome 6.4.0
- **JavaScript**: Vanilla JS con validación en tiempo real

### Procesamiento de Documentos
- **DOCX**: python-docx
- **Excel**: openpyxl
- **PDF**: PyPDF2
- **Imágenes**: Pillow, Wand
- **HTML/CSS**: BeautifulSoup4, lxml

### Herramientas de Desarrollo
- **Formateo**: Black, isort
- **Linting**: flake8
- **Testing**: factory-boy, faker
- **Tareas Asíncronas**: Celery + Redis

## 🚀 Instalación

### Prerrequisitos

- Python 3.8+
- PostgreSQL 13+
- Git

### 1. Clonar el Repositorio

```bash
git clone https://github.com/OscarZarcoG/parse-html.git
cd parse-html
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Base de Datos

```sql
-- Crear base de datos en PostgreSQL
CREATE DATABASE bd_parseo_documentos;
CREATE USER postgres WITH PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE bd_parseo_documentos TO postgres;
```

### 5. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```env
SECRET_KEY=tu_clave_secreta_aqui
DEBUG=True
DB_NAME=bd_parseo_documentos
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
```

### 6. Ejecutar Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Crear Superusuario

```bash
python manage.py createsuperuser
```

### 8. Ejecutar Servidor de Desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en: `http://127.0.0.1:8000`

## 📖 Uso

### 1. Acceso al Sistema

- **URL de Login**: `http://127.0.0.1:8000/auth/login/`
- **Panel de Administración**: `http://127.0.0.1:8000/admin/`

### 2. Subir Documentos

1. Acceder al dashboard principal
2. Hacer clic en "Subir Documento"
3. Seleccionar archivo (DOCX, XLS, XLSX, PDF)
4. El sistema procesará automáticamente el documento

### 3. Gestión de Plantillas

- **Ver Plantillas**: Lista de todas las plantillas generadas
- **Editar Plantillas**: Modificar HTML, CSS y JS
- **Control de Versiones**: Crear ramas, commits y fusiones
- **Vista Previa**: Previsualizar plantillas en tiempo real

### 4. Roles de Usuario

- **Admin**: Acceso completo al sistema
- **Editor**: Puede crear y editar plantillas
- **Visualizador**: Solo puede ver plantillas existentes

## 📁 Estructura del Proyecto

```
parse-HTML/
├── AUTH/                   # Módulo de autenticación
│   ├── models.py          # Modelo de usuario personalizado
│   ├── views.py           # Vistas de login/registro
│   └── templates/         # Plantillas de autenticación
├── PARSER/                # Módulo de procesamiento
│   ├── models.py          # Modelos de documentos
│   ├── services.py        # Lógica de parseo
│   └── views.py           # Vistas de procesamiento
├── TEMPLATES/             # Módulo de plantillas
│   ├── models.py          # Modelos de plantillas
│   └── views.py           # Gestión de plantillas
├── VERSIONS/              # Módulo de control de versiones
│   ├── models.py          # Modelos de versionado
│   └── views.py           # Gestión de versiones
├── ParseoDocumentos/      # Configuración principal
│   ├── settings.py        # Configuración de Django
│   └── urls.py            # URLs principales
├── static/                # Archivos estáticos
├── media/                 # Archivos subidos
├── requirements.txt       # Dependencias Python
└── manage.py             # Script de gestión Django
```

## 🔌 API Endpoints

### Autenticación
```
POST /auth/login/          # Iniciar sesión
POST /auth/register/       # Registrar usuario
POST /auth/logout/         # Cerrar sesión
```

### Documentos
```
GET    /api/documents/     # Listar documentos
POST   /api/documents/     # Subir documento
GET    /api/documents/{id}/ # Obtener documento
DELETE /api/documents/{id}/ # Eliminar documento
```

### Plantillas
```
GET    /api/templates/     # Listar plantillas
POST   /api/templates/     # Crear plantilla
GET    /api/templates/{id}/ # Obtener plantilla
PUT    /api/templates/{id}/ # Actualizar plantilla
DELETE /api/templates/{id}/ # Eliminar plantilla
```

### Versiones
```
GET    /api/versions/      # Listar versiones
POST   /api/versions/      # Crear versión
GET    /api/branches/      # Listar ramas
POST   /api/branches/      # Crear rama
```

## 🧪 Testing

```bash
# Ejecutar todas las pruebas
python manage.py test

# Ejecutar pruebas de un módulo específico
python manage.py test AUTH
python manage.py test PARSER
```

## 🤝 Contribución

1. **Fork** el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -am 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Crear un **Pull Request**

### Estándares de Código

- Usar **Black** para formateo de código
- Seguir **PEP 8** para estilo de Python
- Escribir **docstrings** para funciones y clases
- Incluir **tests** para nuevas características

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 👥 Autores

- **Tu Nombre** - *Desarrollo inicial* - [OscarZarcoG](https://github.com/OscarZarcoG)

## 🆘 Soporte

Si encuentras algún problema o tienes preguntas:

1. Revisa los [Issues existentes](https://github.com/OscarZarcoG/parse-html/issues)
2. Crea un [nuevo Issue](https://github.com/OscarZarcoG/parse-html/issues/new)
3. Contacta al equipo de desarrollo

## 📈 Roadmap

- [ ] Soporte para más formatos de documento (PPTX, ODT)
- [ ] Integración con servicios de almacenamiento en la nube
- [ ] Editor visual de plantillas
- [ ] Exportación a múltiples formatos
- [ ] API GraphQL
- [ ] Aplicación móvil

---

**ParseDoc System** - Transformando documentos en plantillas web inteligentes