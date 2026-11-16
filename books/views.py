import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
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


class HtmxPartialMixin:
    """Render `partial_template_name` for HTMX requests, the full page otherwise.

    A history restore (back button with no cached snapshot) gets the whole
    page even though it arrives as an HTMX request. Every response varies on
    the HX-Request header, so the browser caches the partial and the full page
    separately and never shows a bare partial when you go back to the URL.
    """

    partial_template_name = None

    def get_template_names(self):
        htmx = self.request.htmx
        if htmx and not htmx.history_restore_request:
            return [self.partial_template_name]
        return super().get_template_names()

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        patch_vary_headers(response, ["HX-Request"])
        return response


class SearchCatalogView(LoginRequiredMixin, HtmxPartialMixin, TemplateView):
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


class SavedBooksView(LoginRequiredMixin, HtmxPartialMixin, TemplateView):
    """Saved Books: the signed-in user's own saves.

    Built only from the local database, so it keeps working when Open Library
    is down. Search, filters and sort come from the URL and are applied by
    `services.filter_saved_books`, which holds every list rule. Shows PER_PAGE
    saves per page; an invalid or out-of-range page shows the nearest real
    page instead of an error.

    HTMX requests from the toolbar and pagination get only the list partial,
    and the HX-Push-Url header puts the tidy URL for the current settings
    (without empty or invalid values) in the address bar.
    """

    template_name = "books/saved_books.html"
    partial_template_name = "books/_saved_books_list.html"
    PER_PAGE = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        own_saves = SavedBook.objects.filter(user=self.request.user)
        result = services.filter_saved_books(
            own_saves.select_related("book"), self.request.GET
        )
        filters = result.filters
        paginator = Paginator(result.saves, self.PER_PAGE)
        page_obj = paginator.get_page(self.request.GET.get("page"))
        page = page_obj.number
        path = self.request.path
        query = urlencode({**filters, "page": page} if page > 1 else filters)
        self.current_url = f"{path}?{query}" if query else path
        context.update(
            saves=page_obj.object_list,
            total_saves=paginator.count,
            # Tells "no saves yet" apart from "nothing matches these filters".
            has_any_saves=bool(paginator.count) or own_saves.exists(),
            filters=filters,
            is_filtered=any(key != "sort" for key in filters),
            status_choices=SavedBook.Status.choices,
            rating_choices=[(str(n), "★" * n) for n in range(5, 0, -1)],
            sort_choices=[
                (key, label) for key, (label, _) in services.SAVED_BOOK_SORTS.items()
            ],
            default_sort=services.DEFAULT_SORT,
            page=page,
            num_pages=paginator.num_pages,
            prev_url=(
                page_url(path, filters, page - 1) if page_obj.has_previous() else None
            ),
            next_url=(
                page_url(path, filters, page + 1) if page_obj.has_next() else None
            ),
        )
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        htmx = self.request.htmx
        if htmx and not htmx.history_restore_request:
            response["HX-Push-Url"] = self.current_url
        return response


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
