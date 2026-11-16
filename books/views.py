from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def saved_books(request):
    """The user's Saved Books. A members-only placeholder until Phase 6."""
    return render(request, "books/saved_books.html")
