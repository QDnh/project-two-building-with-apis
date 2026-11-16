from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("catalog/", views.SearchCatalogView.as_view(), name="search_catalog"),
    path("saved/", views.SavedBooksView.as_view(), name="saved_books"),
    path("books/<str:work_id>/", views.BookDetailView.as_view(), name="book_detail"),
]
