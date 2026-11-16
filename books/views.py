import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import DetailView, TemplateView

from . import openlibrary, services
from .models import Book, SavedBook

logger = logging.getLogger(__name__)

# Save button text by where the button is shown; anywhere else uses "Save".
SAVE_LABELS = {"book_page": "Save to my library"}


def parse_page(value):
    """Read a 1-based page number from the URL; anything invalid means page 1."""
    try:
        page = int(value)
    except TypeError, ValueError:
        return 1
    return max(page, 1)


def page_url(path, params, page):
    """Return `path` with `params` plus `page` as a query string."""
    return f"{path}?{urlencode({**params, 'page': page})}"


class SearchCatalogView(LoginRequiredMixin, TemplateView):
    """Search Catalog: search Open Library and show one page of results.

    With no `q` in the URL the page shows just the search form. An empty `q`
    is rejected without calling Open Library. A failed search shows an alert
    in the results area; the technical error is logged here.

    Results come 20 per page, with the query and page number in the URL.
    Paging stops at MAX_PAGES (to steer people toward better searches and stay
    within Open Library's rate limits); a higher page number is capped and
    shows a hint to refine the search. HTMX requests from the pagination
    buttons get only the results partial.
    """

    template_name = "books/search_catalog.html"
    partial_template_name = "books/_search_results.html"
    MAX_PAGES = 10

    def get_template_names(self):
        htmx = self.request.htmx
        # A history restore (back button with no cached snapshot) needs the
        # whole page, even though it arrives as an HTMX request.
        if htmx and not htmx.history_restore_request:
            return [self.partial_template_name]
        return [self.template_name]

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

        page = parse_page(self.request.GET.get("page"))
        capped = page > self.MAX_PAGES
        page = min(page, self.MAX_PAGES)
        per_page = openlibrary.RESULTS_PER_PAGE

        try:
            search_page = openlibrary.search_books(query, page=page, limit=per_page)
        except openlibrary.SearchError as error:
            logger.warning(
                "Open Library search failed for %r: %s",
                query,
                error,
                exc_info=error.__cause__ is not None,
            )
            context["search_error"] = str(error)
            return context

        total_pages = -(-search_page.total // per_page)  # ceiling division
        num_pages = max(min(total_pages, self.MAX_PAGES), 1)
        params = {"q": context["query"]}
        path = self.request.path
        first = (page - 1) * per_page + 1
        result_ids = [result.work_id for result in search_page.results]
        context.update(
            search_page=search_page,
            # Results the user already has show "Saved ✓" instead of Save.
            saved_work_ids=set(
                SavedBook.objects.filter(
                    user=self.request.user, book__work_id__in=result_ids
                ).values_list("book__work_id", flat=True)
            ),
            page=page,
            num_pages=num_pages,
            first_index=first,
            last_index=first + len(search_page.results) - 1,
            first_page_url=page_url(path, params, 1),
            prev_url=page_url(path, params, page - 1) if page > 1 else None,
            next_url=(page_url(path, params, page + 1) if page < num_pages else None),
            # Show the hint when someone asked past the cap, or is on the last
            # allowed page while Open Library has more matches.
            show_refine_hint=capped
            or (page == self.MAX_PAGES and total_pages > self.MAX_PAGES),
        )
        return context


class SaveBookView(LoginRequiredMixin, View):
    """Save a book to the user's Saved Books by its work ID.

    Only the work ID is taken from the request; book details come from the
    database or Open Library through the shared save function. If Open Library
    fails, the alert appears next to the book's Save button and the technical
    error is logged here.

    HTMX requests get the save control back ("Saved ✓", "already saved", or
    the Save button with an alert). Without JavaScript the form posts normally
    and the user is redirected back to the page they came from, with a message.
    """

    http_method_names = ["post"]

    def post(self, request, work_id):
        source = request.POST.get("source", "")
        context = {
            "work_id": work_id,
            "is_saved": False,
            "source": source,
            "label": SAVE_LABELS.get(source, "Save"),
            "next": self.get_next_url(work_id),
        }
        try:
            services.save_book(request.user, work_id)
        except services.InvalidWorkId:
            raise Http404("Not a valid Open Library work ID.") from None
        except services.AlreadySaved as error:
            context.update(is_saved=True, already_saved=True)
            message_level, message = messages.INFO, str(error)
        except openlibrary.SearchError as error:
            logger.warning(
                "Saving %s failed: %s",
                work_id,
                error,
                exc_info=error.__cause__ is not None,
            )
            context["save_error"] = str(error)
            message_level = messages.ERROR
            message = f"{error} Your saved books are still available."
        else:
            context["is_saved"] = True
            message_level, message = messages.SUCCESS, "Saved to your Saved Books."

        if request.htmx:
            return render(request, "books/_save_control.html", context)
        messages.add_message(request, message_level, message)
        return redirect(context["next"])

    def get_next_url(self, work_id):
        """Where a no-JavaScript save returns to: the posted `next` if it's a
        page on this site, otherwise Search Catalog."""
        next_url = self.request.POST.get("next", "")
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_url
        return reverse("books:search_catalog")


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
        # Only the viewer's own save is ever looked up, never anyone else's.
        user = self.request.user
        context["own_save"] = (
            self.object.saves.filter(user=user).first()
            if user.is_authenticated
            else None
        )
        return context
