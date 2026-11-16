from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("catalog/", views.SearchCatalogView.as_view(), name="search_catalog"),
    path("saved/", views.SavedBooksView.as_view(), name="saved_books"),
    path(
        "saved/<int:pk>/edit/",
        views.UpdateSavedBookView.as_view(),
        name="update_saved_book",
    ),
    path(
        "saved/<int:pk>/remove/",
        views.RemoveSavedBookView.as_view(),
        name="remove_saved_book",
    ),
    path("books/<str:work_id>/", views.BookDetailView.as_view(), name="book_detail"),
    path("books/<str:work_id>/save/", views.SaveBookView.as_view(), name="save_book"),
]
