from django.contrib import admin

from .models import Book, SavedBook


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "authors", "first_publish_year", "work_id"]
    search_fields = ["title", "authors", "work_id"]


@admin.register(SavedBook)
class SavedBookAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "status", "rating", "is_public", "saved_at"]
    list_filter = ["status", "rating", "is_public"]
    search_fields = ["user__username", "book__title"]
    list_select_related = ["user", "book"]
    raw_id_fields = ["book"]
