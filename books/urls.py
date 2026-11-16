from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("saved/", views.saved_books, name="saved_books"),
]
