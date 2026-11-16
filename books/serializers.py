"""API serializers. Book details are always read-only: they come only from
Open Library, never from data a client sends."""

from rest_framework import serializers

from .models import Book, SavedBook


class BookSerializer(serializers.ModelSerializer):
    """A book's stored details, with authors as a list."""

    authors = serializers.ListField(
        source="author_list", child=serializers.CharField(), read_only=True
    )
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "work_id",
            "title",
            "authors",
            "first_publish_year",
            "cover_id",
            "cover_url",
            "edition_count",
            "isbns",
            "subjects",
        ]
        read_only_fields = fields

    def get_cover_url(self, book):
        return book.cover_url()


class BookDetailSerializer(BookSerializer):
    """A book plus its anonymous community average and rating count.

    Built from Book.community_rating(), which only aggregates: no user
    information ever appears here. The average is a one-decimal string
    ("4.3"), or null when nobody has rated the book yet.
    """

    community_average = serializers.DecimalField(
        max_digits=2, decimal_places=1, read_only=True, allow_null=True
    )
    rating_count = serializers.IntegerField(read_only=True)

    class Meta(BookSerializer.Meta):
        fields = [*BookSerializer.Meta.fields, "community_average", "rating_count"]
        read_only_fields = fields

    def to_representation(self, book):
        rating = book.community_rating()
        book.community_average = rating.average
        book.rating_count = rating.count
        return super().to_representation(book)


class SavedBookSerializer(serializers.ModelSerializer):
    """One of the requester's own saves, with the book nested read-only.

    Edits are validated and applied by `services.update_saved_book`, the same
    function the website uses; these fields describe the output and the
    browsable API's edit form.
    """

    book = BookSerializer(read_only=True)
    status = serializers.ChoiceField(choices=SavedBook.Status.choices)

    class Meta:
        model = SavedBook
        fields = ["id", "book", "status", "rating", "is_public", "saved_at"]
        read_only_fields = ["id", "book", "saved_at"]


class PublicSavedBookSerializer(serializers.ModelSerializer):
    """A public save as anyone may see it: the book, status and rating."""

    book = BookSerializer(read_only=True)

    class Meta:
        model = SavedBook
        fields = ["book", "status", "rating", "saved_at"]
        read_only_fields = fields


class SavedBookCreateSerializer(serializers.Serializer):
    """Saving a book takes only its Open Library work ID; any book details
    sent alongside it are ignored."""

    work_id = serializers.CharField(max_length=20)
