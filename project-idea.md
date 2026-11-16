We need to build a new Django application named Book Catalog System. This application is a tool that will be used by consumers to search for, save, set status, and rate books. Both the technology requirements and business requirements are outlined below.

Technology requirments:
- Python
- Django
- Django REST Framework (DRF)
- SQLite
- uv
- Ruff
- Tailwind CSS with DaisyUI using django-tailwind-cli
- HTMX (to minimize unnecessary page reloads)
- pytest

Business requirements:
- Must have one cohesive purpose.
- Users must be able to search for books through an external API.
- Users must be able to save selected books to the application, and store enough information locally in case the external API becomes unavailable.
- Users must be able to add and edit their own information (set read status (if they have read a book), and set 1-5 full star rating).
- Users must be able to browse saved books on a website; search feature, filtering, sorting, and pagination; these features must operate on locally saved data.
- Users must be able to sign in (email, public username, password), and must be signed in to modify their saved data; saved data is private unless a user selects to share it; enforced by both website and API.
- Application must provide its own API, that supports listing, creating, updating, and deleting saved entries.
- Application must be able to handle unsuccessful external requests; must show a useful message when the external API is unavailable or a request fails.