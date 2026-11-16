from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("saved/", views.SavedBooksView.as_view(), name="saved_books"),
    path("books/<str:work_id>/", views.BookDetailView.as_view(), name="book_detail"),
]
