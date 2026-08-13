from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models


class DocumentType(models.Model):
    """Tipo de documento que se puede subir al sistema (Factura, Contrato, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=50, unique=True, help_text="Identificador corto, ej: 'factura'")

    def __str__(self):
        return self.name


class ValidationRule(models.Model):
    """
    Configuración: define qué grupo es responsable de validar
    cada tipo de documento. Esto reemplaza los 'if' hardcodeados.
    """
    document_type = models.OneToOneField(
        DocumentType,
        on_delete=models.CASCADE,
        related_name='validation_rule',
    )
    responsible_group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='validation_rules',
        help_text="Grupo responsable de validar este tipo de documento",
    )

    def __str__(self):
        return f"{self.document_type.name} → {self.responsible_group.name}"


class Document(models.Model):
    """Documento subido por un usuario, almacenado en AWS S3."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        IN_REVIEW = 'in_review', 'En Revisión'
        APPROVED = 'approved', 'Aprobado'
        REJECTED = 'rejected', 'Rechazado'

    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name='documents',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_documents',
    )
    related_entity = models.CharField(
        max_length=255,
        help_text="Referencia al registro del sistema al que pertenece este documento",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.document_type.name} - {self.get_status_display()}"


class ValidationTask(models.Model):
    """Tarea de validación creada para un documento, asignada a un grupo responsable."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        IN_REVIEW = 'in_review', 'En Revisión'
        APPROVED = 'approved', 'Aprobado'
        REJECTED = 'rejected', 'Rechazado'

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='validation_task',
    )
    assigned_group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name='validation_tasks',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decided_tasks',
    )
    decision_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Tarea #{self.id} - {self.document} - {self.get_status_display()}"