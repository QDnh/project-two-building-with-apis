from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Count, Sum
from django.urls import reverse

ONE_DECIMAL = Decimal("0.1")

# Only the first few ISBNs and subjects are kept; Open Library can return hundreds.
MAX_LIST_VALUES = 10

# Authors are stored in one text field, joined with this separator.
AUTHOR_SEPARATOR = "; "

COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg"

# A short-form Open Library work ID, e.g. OL893414W.
WORK_ID_PATTERN = r"^OL\d+W$"


class CommunityRating(NamedTuple):
    """The anonymous average of every rating a book has, and how many there are."""

    average: Decimal | None
    count: int


class Book(models.Model):
    """One Open Library work, shared by every user who saves it."""

    work_id = models.CharField(
        "Open Library work ID",
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(WORK_ID_PATTERN, "Enter a work ID like OL893414W."),
        ],
        help_text="Short form, e.g. OL893414W. Used in the book page URL.",
    )
    title = models.CharField(max_length=500)
    authors = models.TextField(
        blank=True, help_text=f"Author names joined with {AUTHOR_SEPARATOR!r}."
    )
    first_publish_year = models.PositiveSmallIntegerField(null=True, blank=True)
    cover_id = models.PositiveIntegerField(
        "Open Library cover ID", null=True, blank=True
    )
    edition_count = models.PositiveIntegerField(default=0)
    isbns = models.JSONField(default=list, blank=True)
    subjects = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.work_id})"

    def save(self, *args, **kwargs):
        self.isbns = list(self.isbns or [])[:MAX_LIST_VALUES]
        self.subjects = list(self.subjects or [])[:MAX_LIST_VALUES]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("books:book_detail", args=[self.work_id])

    @property
    def author_list(self):
        return [name.strip() for name in self.authors.split(";") if name.strip()]

    def cover_url(self, size="M"):
        """Cover image URL from Open Library's cover service, or None."""
        if self.cover_id is None:
            return None
        return COVER_URL.format(cover_id=self.cover_id, size=size)

    @property
    def cover_url_large(self):
        return self.cover_url("L")

    def community_rating(self):
        """Average (one decimal) and count of all ratings, public and private."""
        totals = self.saves.filter(rating__isnull=False).aggregate(
            total=Sum("rating"), count=Count("rating")
        )
        count = totals["count"]
        if not count:
            return CommunityRating(average=None, count=0)
        # Exact decimal division, then round half up (4.25 → 4.3, not 4.2).
        average = (Decimal(totals["total"]) / count).quantize(
            ONE_DECIMAL, rounding=ROUND_HALF_UP
        )
        return CommunityRating(average=average, count=count)


class SavedBookQuerySet(models.QuerySet):
    def public(self):
        """Saves their owners chose to share: the only saves anyone else may see.

        This is the privacy rule. Every profile page and public API endpoint
        lists saves through this method and nothing else.
        """
        return self.filter(is_public=True)


class SavedBook(models.Model):
    """One user's save of a book, with their own status, rating and sharing."""

    class Status(models.TextChoices):
        WANT_TO_READ = "want_to_read", "Want to read"
        READING = "reading", "Reading"
        READ = "read", "Read"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_books",
    )
    # PROTECT: a book someone has saved can never be deleted out from under them.
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="saves")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WANT_TO_READ
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    is_public = models.BooleanField("public", default=False)
    saved_at = models.DateTimeField("date saved", auto_now_add=True)

    objects = SavedBookQuerySet.as_manager()

    class Meta:
        ordering = ["-saved_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"], name="unique_saved_book_per_user"
            ),
            # Backs up the validators: empty ("Not rated") or 1–5 stars.
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True)
                | models.Q(rating__gte=1, rating__lte=5),
                name="saved_book_rating_empty_or_1_to_5",
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.book.title}"
