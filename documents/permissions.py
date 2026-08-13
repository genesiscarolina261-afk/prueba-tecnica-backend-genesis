from rest_framework.permissions import BasePermission


class IsAssignedGroupMember(BasePermission):
    """
    Permite la acción solo si el usuario autenticado pertenece
    al grupo responsable asignado en la ValidationTask del documento.
    """
    message = "No perteneces al grupo responsable de validar este documento."

    def has_object_permission(self, request, view, document):
        task = getattr(document, 'validation_task', None)
        if task is None:
            return False
        user_groups = request.user.groups.all()
        return task.assigned_group in user_groups