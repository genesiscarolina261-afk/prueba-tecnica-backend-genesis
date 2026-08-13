from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Document, DocumentType, ValidationRule, ValidationTask


class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ['id', 'name', 'code']


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer para SUBIR un documento nuevo."""

    class Meta:
        model = Document
        fields = ['id', 'file', 'document_type', 'related_entity', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']

    def create(self, validated_data):
    
        request = self.context['request']
        validated_data['uploaded_by'] = request.user
        return super().create(validated_data)


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer para VER el detalle de un documento (incluye info de la tarea)."""

    document_type = DocumentTypeSerializer(read_only=True)
    uploaded_by = serializers.StringRelatedField()
    file_url = serializers.SerializerMethodField()
    assigned_group = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'file_url', 'document_type', 'uploaded_by',
            'related_entity', 'status', 'assigned_group',
            'created_at', 'updated_at',
        ]

    def get_file_url(self, obj):

        return obj.file.url if obj.file else None

    def get_assigned_group(self, obj):
        task = getattr(obj, 'validation_task', None)
        return task.assigned_group.name if task else None


class ValidationDecisionSerializer(serializers.Serializer):
    """Serializer para aprobar/rechazar un documento."""
    notes = serializers.CharField(required=False, allow_blank=True, default='')