"""Load demo users, real books and a mix of saves, without touching the network.

Usage:
    uv run python manage.py seed_demo

The books come from `books/data/demo_books.json`, a snapshot of real Open
Library search results bundled with the project. Running the command again
resets the demo users' passwords and demo saves to the values below instead of
creating duplicates. It refuses to run unless DEBUG is on, so demo accounts
with known passwords never reach a real deployment.
"""

import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from books.models import AUTHOR_SEPARATOR, Book, SavedBook

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "demo_books.json"

# Every demo account uses this password. Documented in the README.
DEMO_PASSWORD = "shelf-demo-2026"

READ = SavedBook.Status.READ
READING = SavedBook.Status.READING
WANT = SavedBook.Status.WANT_TO_READ
PUBLIC, PRIVATE = True, False

# username -> saves as (work_id, status, rating, is_public), newest first.
# The mix shows off public and private saves, all three statuses, unrated
# saves, a user with no public saves (dev), a book whose single rating is
# private (The Great Gatsby), and a book nobody has saved (Moby Dick).
DEMO_SAVES = {
    "alice": [
        ("OL893414W", READ, 5, PUBLIC),  # Dune
        ("OL27482W", READ, 4, PUBLIC),  # The Hobbit
        ("OL59800W", READING, None, PUBLIC),  # The Left Hand of Darkness
        ("OL2163649W", WANT, None, PRIVATE),  # The Hitchhiker's Guide…
        ("OL66554W", READ, 3, PRIVATE),  # Pride and Prejudice
    ],
    "ben": [
        ("OL1168083W", READ, 5, PUBLIC),  # Nineteen Eighty-Four
        ("OL64365W", READ, 4, PUBLIC),  # Brave New World
        ("OL103123W", READING, None, PUBLIC),  # Fahrenheit 451
        ("OL893414W", READ, 4, PRIVATE),  # Dune
        ("OL468431W", READ, 2, PRIVATE),  # The Great Gatsby
    ],
    "chloe": [
        ("OL66554W", READ, 5, PUBLIC),  # Pride and Prejudice
        ("OL1095427W", READ, 5, PUBLIC),  # Jane Eyre
        ("OL50548W", WANT, None, PUBLIC),  # Beloved
        ("OL29983W", READING, None, PRIVATE),  # Little Women
        ("OL450063W", READ, 4, PRIVATE),  # Frankenstein
        ("OL893414W", WANT, None, PRIVATE),  # Dune
    ],
    "dev": [
        ("OL27482W", READ, 5, PRIVATE),  # The Hobbit
        ("OL3140822W", READING, None, PRIVATE),  # To Kill a Mockingbird
        ("OL2163649W", READ, 4, PRIVATE),  # The Hitchhiker's Guide…
    ],
}


def load_books():
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


class Command(BaseCommand):
    help = "Load demo users, books and saves from bundled data (DEBUG only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_demo only runs with DEBUG on. Demo accounts have known "
                "passwords and must never be created on a real deployment."
            )

        with transaction.atomic():
            books = self.seed_books()
            users = self.seed_users()
            saves = self.seed_saves(users, books)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {len(books)} books, {len(users)} users, "
                f"{saves} saves."
            )
        )
        self.stdout.write(
            f"Sign in as {', '.join(DEMO_SAVES)} with password {DEMO_PASSWORD!r}."
        )

    def seed_books(self):
        books = {}
        for data in load_books():
            book, _ = Book.objects.update_or_create(
                work_id=data["work_id"],
                defaults={
                    "title": data["title"],
                    "authors": AUTHOR_SEPARATOR.join(data["authors"]),
                    "first_publish_year": data["first_publish_year"],
                    "cover_id": data["cover_id"],
                    "edition_count": data["edition_count"],
                    "isbns": data["isbns"],
                    "subjects": data["subjects"],
                },
            )
            books[book.work_id] = book
        return books

    def seed_users(self):
        users = {}
        for username in DEMO_SAVES:
            user, _ = get_user_model().objects.get_or_create(
                username=username, defaults={"email": f"{username}@example.com"}
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            users[username] = user
        return users

    def seed_saves(self, users, books):
        now = timezone.now()
        count = 0
        for username, saves in DEMO_SAVES.items():
            for days_ago, (work_id, status, rating, is_public) in enumerate(saves):
                saved, _ = SavedBook.objects.update_or_create(
                    user=users[username],
                    book=books[work_id],
                    defaults={
                        "status": status,
                        "rating": rating,
                        "is_public": is_public,
                    },
                )
                # Spread the save dates out so "recently saved" has an order.
                # saved_at is auto_now_add, so set it with an update.
                SavedBook.objects.filter(pk=saved.pk).update(
                    saved_at=now - timedelta(days=days_ago)
                )
                count += 1
        return count
