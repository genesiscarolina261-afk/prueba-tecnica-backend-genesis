from django.urls import path

from .views import (
    ApproveDocumentView,
    DocumentDetailView,
    DocumentUploadView,
    PendingDocumentsListView,
    RejectDocumentView,
)

urlpatterns = [
    path('', DocumentUploadView.as_view(), name='document-upload'),
    path('pending/', PendingDocumentsListView.as_view(), name='document-pending'),
    path('<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('<int:pk>/approve/', ApproveDocumentView.as_view(), name='document-approve'),
    path('<int:pk>/reject/', RejectDocumentView.as_view(), name='document-reject'),
]