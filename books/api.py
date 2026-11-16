"""The app's REST API (Django REST Framework).

Uses the same shared logic as the website (`services`) and the same privacy
rule (`SavedBook.objects.public()`).
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from accounts.models import User

from . import openlibrary, services
from .models import Book, SavedBook
from .serializers import (
    BookDetailSerializer,
    PublicSavedBookSerializer,
    SavedBookCreateSerializer,
    SavedBookSerializer,
)

logger = logging.getLogger(__name__)


class OpenLibraryUnavailable(APIException):
    """Open Library couldn't provide a book new to the app: try again later."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "open_library_unavailable"


class SavedBookViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """The signed-in user's own saves: list, create, retrieve, update, delete.

    Create takes only a work ID and goes through `services.save_book`, so book
    details come from the database or Open Library, never from the request.
    Updates (PATCH) go through `services.update_saved_book`: only status,
    rating and is_public can change, and invalid values change nothing (400).
    """

    serializer_class = SavedBookSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        # Only the requester's own saves exist here, so another user's save is
        # a 404, exactly like one that doesn't exist (never a 403).
        return SavedBook.objects.filter(user=self.request.user).select_related("book")

    def get_serializer_class(self):
        # The browsable API's form shows only the work ID field for create.
        if self.action == "create":
            return SavedBookCreateSerializer
        return SavedBookSerializer

    def create(self, request, *args, **kwargs):
        serializer = SavedBookCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        work_id = serializer.validated_data["work_id"]
        try:
            save = services.save_book(request.user, work_id)
        except services.InvalidWorkId:
            raise ValidationError(
                {"work_id": ["Enter an Open Library work ID like OL893414W."]}
            ) from None
        except services.AlreadySaved as error:
            raise ValidationError({"work_id": [str(error)]}) from None
        except openlibrary.SearchError as error:
            logger.warning(
                "API save of %s failed: %s",
                work_id,
                error,
                exc_info=error.__cause__ is not None,
            )
            raise OpenLibraryUnavailable(str(error)) from error
        return Response(SavedBookSerializer(save).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        save = self.get_object()
        if not hasattr(request.data, "keys"):
            raise ValidationError({"detail": ["Send a JSON object or form data."]})
        try:
            services.update_saved_book(save, request.data)
        except services.InvalidUpdate as error:
            raise ValidationError(
                {field: [message] for field, message in error.errors.items()}
            ) from None
        return Response(SavedBookSerializer(save).data)


class PublicSavedBookListAPIView(generics.ListAPIView):
    """A user's public saves, read-only and open to anyone.

    Lists saves only through `SavedBook.objects.public()`, exactly like the
    profile page, so private saves never appear. Unknown usernames are 404.
    """

    serializer_class = PublicSavedBookSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs["username"])
        return SavedBook.objects.filter(user=user).public().select_related("book")


class BookDetailAPIView(generics.RetrieveAPIView):
    """A book by its work ID: details plus the anonymous community average.

    Read-only and open to anyone. Contains no user information.
    """

    queryset = Book.objects.all()
    serializer_class = BookDetailSerializer
    lookup_field = "work_id"
    permission_classes = [permissions.AllowAny]
