from django.conf import settings
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from books.models import SavedBook
from books.views import HtmxPartialMixin, page_url

from .forms import SignUpForm
from .models import User


class SignUpView(CreateView):
    """Create an account and sign the new user straight in."""

    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy(settings.LOGIN_REDIRECT_URL)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)  # saves the user as self.object
        login(self.request, self.object)
        return response


class ProfileView(HtmxPartialMixin, TemplateView):
    """A user's public profile: their public saves, with status and rating.

    Open to everyone. Saves are listed only through `SavedBook.objects.public()`,
    so private saves never appear here, not even to the owner.
    """

    template_name = "accounts/profile.html"
    partial_template_name = "accounts/_profile_saves.html"
    PER_PAGE = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = get_object_or_404(User, username=kwargs["username"])
        saves = SavedBook.objects.filter(user=profile_user).public()
        paginator = Paginator(saves.select_related("book"), self.PER_PAGE)
        page_obj = paginator.get_page(self.request.GET.get("page"))
        page = page_obj.number
        path = self.request.path
        context.update(
            profile_user=profile_user,
            saves=page_obj.object_list,
            total_saves=paginator.count,
            page=page,
            num_pages=paginator.num_pages,
            prev_url=page_url(path, {}, page - 1) if page_obj.has_previous() else None,
            next_url=page_url(path, {}, page + 1) if page_obj.has_next() else None,
        )
        return context
