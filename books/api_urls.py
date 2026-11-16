from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import api

app_name = "api"

router = DefaultRouter()
router.register("saved-books", api.SavedBookViewSet, basename="saved-book")

urlpatterns = [
    path("token/", obtain_auth_token, name="token"),
    path(
        "users/<str:username>/saved-books/",
        api.PublicSavedBookListAPIView.as_view(),
        name="public_saved_books",
    ),
    path("books/<str:work_id>/", api.BookDetailAPIView.as_view(), name="book"),
    *router.urls,
]
