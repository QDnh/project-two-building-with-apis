import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, TemplateView

from . import openlibrary
from .models import Book

logger = logging.getLogger(__name__)


class SearchCatalogView(LoginRequiredMixin, TemplateView):
    """Search Catalog: search Open Library and show one page of results.

    With no `q` in the URL the page shows just the search form. An empty `q`
    is rejected without calling Open Library. A failed search shows an alert
    in the results area; the technical error is logged here.
    """

    template_name = "books/search_catalog.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raw_query = self.request.GET.get("q")
        context["query"] = (raw_query or "").strip()
        context["searched"] = raw_query is not None
        if raw_query is None:
            return context

        query = openlibrary.clean_query(raw_query)
        if not query:
            context["form_error"] = (
                "Enter a title, author, keywords or an ISBN to search."
            )
            return context

        try:
            context["search_page"] = openlibrary.search_books(query)
        except openlibrary.SearchError as error:
            logger.warning(
                "Open Library search failed for %r: %s",
                query,
                error,
                exc_info=error.__cause__ is not None,
            )
            context["search_error"] = str(error)
        return context


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
