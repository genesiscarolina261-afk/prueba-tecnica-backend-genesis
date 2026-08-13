from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from django.contrib.auth.models import User, Group
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
 
from documents.models import (
    Document,
    DocumentType,
    ValidationRule,
    ValidationTask,
)
 
 
class AuthenticationTests(APITestCase):
 
    def setUp(self):
        self.user = User.objects.create_user(
            username="usuario_test",
            password="Password123"
        )
 
    def test_usuario_no_autenticado_no_puede_ver_documentos_pendientes(self):
        url = reverse("document-pending")
 
        response = self.client.get(url)
 
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )
 
    def test_usuario_autenticado_puede_ver_documentos_pendientes(self):
        self.client.force_authenticate(user=self.user)
 
        url = reverse("document-pending")
 
        response = self.client.get(url)
 
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
 
 
class PendingDocumentsTests(APITestCase):
 
    def setUp(self):
 
        self.contabilidad = Group.objects.create(
            name="Contabilidad"
        )
 
        self.rrhh = Group.objects.create(
            name="Recursos Humanos"
        )
 
        self.usuario_contabilidad = User.objects.create_user(
            username="contador",
            password="Password123"
        )
 
        self.usuario_contabilidad.groups.add(
            self.contabilidad
        )
 
        self.factura = DocumentType.objects.create(
            name="Factura",
            code="factura"
        )
 
        self.contrato = DocumentType.objects.create(
            name="Contrato",
            code="contrato"
        )
 
        ValidationRule.objects.create(
            document_type=self.factura,
            responsible_group=self.contabilidad
        )
 
        ValidationRule.objects.create(
            document_type=self.contrato,
            responsible_group=self.rrhh
        )
 
        self.documento_factura = Document.objects.create(
            file="documents/factura.pdf",
            document_type=self.factura,
            uploaded_by=self.usuario_contabilidad,
            related_entity="FACT-001",
            status=Document.Status.PENDING,
        )
 
        self.documento_contrato = Document.objects.create(
            file="documents/contrato.pdf",
            document_type=self.contrato,
            uploaded_by=self.usuario_contabilidad,
            related_entity="CONT-001",
            status=Document.Status.PENDING,
        )
 
        ValidationTask.objects.create(
            document=self.documento_factura,
            assigned_group=self.contabilidad
        )
 
        ValidationTask.objects.create(
            document=self.documento_contrato,
            assigned_group=self.rrhh
        )
 
    def test_usuario_solo_ve_documentos_de_su_grupo(self):
 
        self.client.force_authenticate(
            user=self.usuario_contabilidad
        )
 
        url = reverse("document-pending")
 
        response = self.client.get(url)
 
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
 
        self.assertEqual(
            len(response.data),
            1
        )
 
        self.assertEqual(
            response.data[0]["id"],
            self.documento_factura.id
        )
 
    def test_usuario_de_otro_grupo_no_puede_aprobar_documento(self):
 
        usuario_rrhh = User.objects.create_user(
            username="usuario_rrhh",
            password="Password123"
        )
 
        usuario_rrhh.groups.add(
            self.rrhh
        )
 
        self.client.force_authenticate(
            user=usuario_rrhh
        )
 
        url = reverse(
            "document-approve",
            kwargs={
                "pk": self.documento_factura.id
            }
        )
 
        response = self.client.post(
            url,
            data={}
        )
 
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )
 
    def test_usuario_responsable_puede_aprobar_documento(self):
 
        self.client.force_authenticate(
            user=self.usuario_contabilidad
        )
 
        url = reverse(
            "document-approve",
            kwargs={
                "pk": self.documento_factura.id
            }
        )
 
        response = self.client.post(
            url,
            data={
                "notes": "Factura validada correctamente."
            },
            format="json"
        )
 
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
 
        self.documento_factura.refresh_from_db()
 
        self.assertEqual(
            self.documento_factura.status,
            Document.Status.APPROVED
        )
 
        tarea = self.documento_factura.validation_task
 
        self.assertEqual(
            tarea.status,
            ValidationTask.Status.APPROVED
        )
 
        self.assertEqual(
            tarea.decided_by,
            self.usuario_contabilidad
        )
 
        self.assertEqual(
            tarea.decision_notes,
            "Factura validada correctamente."
        )
 
        self.assertIsNotNone(
            tarea.decided_at
        )
 
    def test_documento_aprobado_no_puede_volver_a_validarse(self):
 
        self.client.force_authenticate(
            user=self.usuario_contabilidad
        )
 
        approve_url = reverse(
            "document-approve",
            kwargs={
                "pk": self.documento_factura.id
            }
        )
 
        response = self.client.post(
            approve_url,
            data={
                "notes": "Factura aprobada."
            },
            format="json"
        )
 
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
 
        response = self.client.post(
            approve_url,
            data={
                "notes": "Intento de segunda aprobación."
            },
            format="json"
        )
 
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
 
    def test_usuario_responsable_puede_rechazar_documento(self):
 
        self.client.force_authenticate(
            user=self.usuario_contabilidad
        )
 
        url = reverse(
            "document-reject",
            kwargs={
                "pk": self.documento_factura.id
            }
        )
 
        response = self.client.post(
            url,
            data={
                "notes": "La factura no cumple con los requisitos."
            },
            format="json"
        )
 
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
 
        self.documento_factura.refresh_from_db()
 
        self.assertEqual(
            self.documento_factura.status,
            Document.Status.REJECTED
        )
 
        tarea = self.documento_factura.validation_task
 
        self.assertEqual(
            tarea.status,
            ValidationTask.Status.REJECTED
        )
 
        self.assertEqual(
            tarea.decided_by,
            self.usuario_contabilidad
        )
 
        self.assertEqual(
            tarea.decision_notes,
            "La factura no cumple con los requisitos."
        )
 
        self.assertIsNotNone(
            tarea.decided_at
        )
 
    @patch("django.db.models.fields.files.FieldFile.save")
    def test_subir_documento_crea_tarea_de_validacion_automaticamente(self, mock_save):
        mock_save.return_value = "documents/factura_nueva.pdf"
 
        self.client.force_authenticate(
            user=self.usuario_contabilidad
        )
 
        url = reverse("document-upload")
 
        archivo = SimpleUploadedFile(
            "factura_nueva.pdf",
            b"contenido de prueba",
            content_type="application/pdf"
        )
 
        response = self.client.post(
            url,
            data={
                "file": archivo,
                "document_type": self.factura.id,
                "related_entity": "FACT-002",
            },
            format="multipart"
        )
 
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )
 
        documento_nuevo = Document.objects.get(related_entity="FACT-002")
 
        self.assertEqual(
            documento_nuevo.status,
            Document.Status.PENDING
        )
 
        tarea = documento_nuevo.validation_task
 
        self.assertEqual(
            tarea.assigned_group,
            self.contabilidad
        )
 
        self.assertEqual(
            tarea.status,
            ValidationTask.Status.PENDING
        )
 