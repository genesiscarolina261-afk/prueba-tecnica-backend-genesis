from django.contrib import admin

from .models import Document, DocumentType, ValidationRule, ValidationTask


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(ValidationRule)
class ValidationRuleAdmin(admin.ModelAdmin):
    list_display = ('document_type', 'responsible_group')
    list_filter = ('responsible_group',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'document_type', 'uploaded_by', 'status', 'created_at')
    list_filter = ('status', 'document_type')
    search_fields = ('related_entity',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ValidationTask)
class ValidationTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'assigned_group', 'status', 'decided_by', 'created_at')
    list_filter = ('status', 'assigned_group')
    readonly_fields = ('created_at', 'decided_at')