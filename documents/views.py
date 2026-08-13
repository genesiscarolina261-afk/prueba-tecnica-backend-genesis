from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, ValidationRule, ValidationTask
from .permissions import IsAssignedGroupMember
from .serializers import (
    DocumentDetailSerializer,
    DocumentUploadSerializer,
    ValidationDecisionSerializer,
)


class DocumentUploadView(generics.CreateAPIView):
    """
    POST /api/documents/
    Sube un documento y crea automáticamente la tarea de validación,
    asignando el responsable según la configuración (ValidationRule).
    """
    serializer_class = DocumentUploadSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def perform_create(self, serializer):
        document = serializer.save()

        try:
            rule = ValidationRule.objects.get(document_type=document.document_type)
        except ValidationRule.DoesNotExist:
            raise ValidationError(
                "No existe una regla de validación configurada para este tipo de documento. "
                "Contacta al administrador."
            )

        ValidationTask.objects.create(
            document=document,
            assigned_group=rule.responsible_group,
        )

        self._notify_responsible(document, rule.responsible_group)

    def _notify_responsible(self, document, group):
        from django.core.mail import send_mail

        members = group.user_set.all()
        emails = [u.email for u in members if u.email]
        if emails:
            send_mail(
                subject=f'Nuevo documento pendiente de validación: {document.document_type.name}',
                message=(
                    f'Se ha subido un nuevo documento ({document.document_type.name}) '
                    f'que requiere tu validación. ID del documento: {document.id}.'
                ),
                from_email='no-reply@pruebatecnica.com',
                recipient_list=emails,
                fail_silently=True,
            )


class PendingDocumentsListView(generics.ListAPIView):
    """
    GET /api/documents/pending/
    Lista los documentos pendientes de validación asignados
    a algún grupo al que pertenece el usuario autenticado.
    """
    serializer_class = DocumentDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_groups = self.request.user.groups.all()
        return Document.objects.filter(
            status=Document.Status.PENDING,
            validation_task__assigned_group__in=user_groups,
        ).select_related('document_type', 'uploaded_by', 'validation_task')


class DocumentDetailView(generics.RetrieveAPIView):
    """
    GET /api/documents/<id>/
    Muestra el detalle de un documento. Si el usuario autenticado
    es parte del grupo responsable y el documento está Pendiente,
    lo pasa automáticamente a 'En Revisión'.
    """
    serializer_class = DocumentDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = Document.objects.select_related('document_type', 'uploaded_by', 'validation_task')

    def retrieve(self, request, *args, **kwargs):
        document = self.get_object()
        task = getattr(document, 'validation_task', None)

        if task and document.status == Document.Status.PENDING:
            user_groups = request.user.groups.all()
            if task.assigned_group in user_groups:
                document.status = Document.Status.IN_REVIEW
                document.save(update_fields=['status', 'updated_at'])
                task.status = ValidationTask.Status.IN_REVIEW
                task.save(update_fields=['status'])

        serializer = self.get_serializer(document)
        return Response(serializer.data)


class BaseDecisionView(APIView):
    """Vista base compartida por Aprobar y Rechazar."""
    permission_classes = [IsAuthenticated, IsAssignedGroupMember]
    target_status = None
    target_task_status = None

    def get_document(self, pk):
        try:
            document = Document.objects.select_related('validation_task').get(pk=pk)
        except Document.DoesNotExist:
            raise ValidationError("El documento no existe.")
        return document

    @transaction.atomic
    def post(self, request, pk):
        document = self.get_document(pk)

        self.check_object_permissions(request, document)

        if document.status in [Document.Status.APPROVED, Document.Status.REJECTED]:
            raise ValidationError("Este documento ya fue validado y no puede modificarse.")

        task = document.validation_task

        serializer = ValidationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get('notes', '')

        document.status = self.target_status
        document.save(update_fields=['status', 'updated_at'])

        task.status = self.target_task_status
        task.decided_by = request.user
        task.decision_notes = notes
        task.decided_at = timezone.now()
        task.save(update_fields=['status', 'decided_by', 'decision_notes', 'decided_at'])

        return Response(
            DocumentDetailSerializer(document, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class ApproveDocumentView(BaseDecisionView):
    """POST /api/documents/<id>/approve/"""
    target_status = Document.Status.APPROVED
    target_task_status = ValidationTask.Status.APPROVED


class RejectDocumentView(BaseDecisionView):
    """POST /api/documents/<id>/reject/"""
    target_status = Document.Status.REJECTED
    target_task_status = ValidationTask.Status.REJECTED