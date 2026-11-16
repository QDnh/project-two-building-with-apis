from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, TemplateView

from .models import Book


class SavedBooksView(LoginRequiredMixin, TemplateView):
    """The user's Saved Books. A members-only placeholder until Phase 6."""

    template_name = "books/saved_books.html"


class BookDetailView(DetailView):
    """A book's page: stored details plus the anonymous community average.

    Open to everyone and built only from the local database, so it keeps
    working when Open Library is down. Unknown work IDs return 404.
    """

    model = Book
    slug_field = "work_id"
    slug_url_kwarg = "work_id"
    template_name = "books/book_detail.html"
    context_object_name = "book"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["community_rating"] = self.object.community_rating()
        return context
