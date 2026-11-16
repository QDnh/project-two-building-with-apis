"""Delete books that nobody has saved.

Usage:
    uv run python manage.py prune_books --dry-run   # list them, delete nothing
    uv run python manage.py prune_books             # delete them

Only books with zero saves (public or private) are removed. SavedBook's link
to Book uses PROTECT, so even if this query were wrong the database would
refuse to delete a book that someone has saved.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Book


class Command(BaseCommand):
    help = "Delete books with zero saves. Use --dry-run to list them first."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the books that would be deleted without deleting them.",
        )

    def handle(self, *args, dry_run=False, **options):
        unsaved = Book.objects.filter(saves__isnull=True).order_by("title")

        with transaction.atomic():
            books = list(unsaved)
            if not books:
                self.stdout.write("No unsaved books to prune.")
                return

            for book in books:
                self.stdout.write(f"  {book.work_id}  {book.title}")

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"Dry run: {len(books)} unsaved book(s) would be deleted. "
                        "Nothing was deleted."
                    )
                )
                return

            Book.objects.filter(pk__in=[book.pk for book in books]).delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {len(books)} unsaved book(s)."))
