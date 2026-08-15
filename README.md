# Prueba técnica backend — Validación de documentos

API construida con Django y Django REST Framework que permite subir documentos, asignar automáticamente un responsable de validación según una configuración (sin condicionales hardcodeados), y que ese responsable apruebe o rechace el documento. Autenticación mediante JWT y almacenamiento de archivos en AWS S3.

# Tecnologías utilizadas

- Python 3.13
- Django 6.1
- Django REST Framework
- djangorestframework-simplejwt autenticación JWT
- boto3 + django-storages integración con AWS S3
- SQLite base de datos, para simplicidad en este entorno de prueba
- pytest + pytest-django pruebas automatizadas

# Requisitos previos

- Python 3.11 o superior
- Una cuenta de AWS con un bucket S3 creado y un usuario IAM con permisos sobre ese bucket

# Instalación y ejecución del proyecto

1. Clonar el repositorio:
```bash
   git clone https://github.com/genesiscarolina261-afk/prueba-tecnica-backend-genesis.git
   cd prueba-tecnica-backend-genesis
```

2. Crear y activar un entorno virtual:
```bash
   python -m venv venv
   venv\Scripts\Activate.ps1      
```

3. Instalar las dependencias:
```bash
   pip install -r requirements.txt
```

4. Crear el archivo `.env` en la raíz del proyecto, usando `.env.example` como referencia, y completar con tus propios valores (SECRET_KEY, credenciales de AWS, etc.).

5. Aplicar las migraciones:
```bash
   python manage.py migrate
```

6. Crear un superusuario (para acceder al panel de administración):
```bash
   python manage.py createsuperuser
```

7. Levantar el servidor:
```bash
   python manage.py runserver
```

La API queda disponible en `http://127.0.0.1:8000/`.

# Configuración inicial de datos (desde el admin)

Antes de poder subir documentos, es necesario configurar, desde `http://127.0.0.1:8000/admin/`:

1. Un group (por ejemplo, "Contabilidad").
2. Un DocumentType (por ejemplo, "Factura").
3. Una ValidationRule que relacione ese tipo de documento con el grupo responsable.
4. Agregar el usuario que validará los documentos a ese grupo.

Esto reemplaza cualquier condicional en el código: el responsable de cada tipo de documento se define completamente desde la configuración.

# Ejecutar las pruebas automatizadas

```bash
pytest
```

Se incluyen 8 pruebas que cubren: autenticación, filtrado de documentos por grupo, permisos (usuario sin autorización no puede aprobar/rechazar), aprobación, rechazo, bloqueo de doble validación, y creación automática de la tarea de validación al subir un documento.

# Documentación de endpoints

Todos los endpoints (excepto login) requieren un header:

# Autenticación

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/token/` | Login. Recibe `username` y `password`, devuelve `access` y `refresh`. |
| POST | `/api/token/refresh/` | Renueva el `access` token usando el `refresh` token. |

**Ejemplo de body para login:**
```json
{
  "username": "admin",
  "password": "contraseña"
}
```

# Documentos

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/documents/` | Sube un documento nuevo (form-data: `file`, `document_type`, `related_entity`). Crea automáticamente la tarea de validación. |
| GET | `/api/documents/pending/` | Lista los documentos pendientes asignados a los grupos del usuario autenticado. |
| GET | `/api/documents/<id>/` | Muestra el detalle de un documento. Si está Pendiente y el usuario pertenece al grupo responsable, pasa automáticamente a "En Revisión". |
| POST | `/api/documents/<id>/approve/` | Aprueba el documento (solo el grupo responsable puede hacerlo). Body opcional: `{"notes": "..."}`. |
| POST | `/api/documents/<id>/reject/` | Rechaza el documento (misma validación de permisos). Body opcional: `{"notes": "..."}`. |

# Estados de un documento

`pending` → `in_review` → `approved` / `rejected`

Un documento en estado `approved` o `rejected` no puede volver a modificarse.

# Decisiones de diseño

**Configuración de responsables sin condicionales:** en vez de usar `if` para determinar quién valida cada tipo de documento, se creó el modelo `ValidationRule`, que relaciona un `DocumentType` con un `Group` de Django. Al subir un documento, el sistema consulta esta tabla para saber a qué grupo asignar la tarea. Agregar un nuevo tipo de documento con su responsable no requiere tocar el código, solo crear un registro desde el panel de administración.

**Responsables por grupo, no por usuario individual:** se usó el modelo `Group` nativo de Django en lugar de asignar un usuario específico como responsable. Esto permite que cualquier miembro del área (por ejemplo, Contabilidad) pueda validar un documento, sin depender de una sola persona. En el video de demostración se usó el usuario `admin` (que pertenece al grupo `contabilidad`) para mostrar el flujo de aprobación y rechazo, pero cualquier otro usuario que pertenezca a ese mismo grupo puede realizar exactamente las mismas acciones (ver pendientes, aprobar, rechazar), ya que la validación de permisos se hace por grupo y no por un usuario específico.

**Estado "En Revisión":** además de los estados mínimos pedidos (Pendiente, Aprobado, Rechazado), se agregó "En Revisión", que se activa automáticamente cuando el responsable consulta el detalle de un documento pendiente. Esto permite distinguir documentos que aún nadie ha revisado de los que ya están en proceso de evaluación.

**Permisos:** se implementó una clase de permiso personalizada (`IsAssignedGroupMember`) que valida que el usuario autenticado (identificado a través del JWT) pertenezca al grupo asignado a la tarea de validación. El usuario que decide siempre se obtiene del token, nunca de un dato enviado en el cuerpo de la petición, por lo que no es posible suplantar a otro usuario modificando manualmente un identificador.

**Almacenamiento en AWS S3 con acceso privado:** el bucket S3 tiene bloqueado el acceso público. Los archivos se sirven mediante URLs firmadas temporales (1 hora de validez), generadas con un usuario IAM de permisos limitados (solo sobre ese bucket específico), en lugar de usar la cuenta raíz de AWS.

**Notificaciones:** se implementó el envío de notificación por correo electrónico al responsable cuando se crea una tarea de validación, usando el backend de consola de Django (`EMAIL_BACKEND` de consola) para simplificar la demostración sin depender de un servidor SMTP real.

**Bloqueo de doble validación:** una vez que un documento pasa a estado `approved` o `rejected`, cualquier intento posterior de aprobar o rechazar devuelve un error 400 con un mensaje explícito.

## Video de demostración

[Pendiente: agregar enlace aquí]