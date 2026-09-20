from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Anyone can read.
    Only authenticated users can modify.
    Only the object's author can modify/delete it.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Support models that use either 'author' or 'user' as the owner field
        owner = getattr(obj, "author", None) or getattr(obj, "user", None)
        return owner == request.user