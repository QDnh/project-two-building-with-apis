"""A small command-line client for the Book Catalog API.

Run the dev server first (and `seed_demo` for sample data), then:

    # 1. List a user's public saves, using the `page` query parameter.
    uv run python scripts/api_client.py list alice --page 1

    # 2. Change the rating on one of your own saves; prints before and after.
    uv run python scripts/api_client.py update --username alice --rating 3
    uv run python scripts/api_client.py update --username alice --rating 3 --save-id 2

`update` signs in with a token from /api/token/. The password comes from
--password, the BOOK_API_PASSWORD environment variable, or a prompt.
Set BOOK_API_URL (or pass --base-url) to use a server other than
http://127.0.0.1:8000.
"""

import argparse
import getpass
import json
import os
import sys

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10  # seconds


class ApiError(Exception):
    """A failed API call, with a message fit to show the user."""


def call(method, url, *, token=None, **kwargs):
    """Send one request and return its JSON body, or raise ApiError."""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    try:
        response = requests.request(
            method, url, headers=headers, timeout=TIMEOUT, **kwargs
        )
    except requests.RequestException as error:
        raise ApiError(f"Could not reach {url}: {error}") from error
    if not response.ok:
        raise ApiError(
            f"{method} {url} returned {response.status_code}: {response.text}"
        )
    return response.json()


def get_token(base_url, username, password):
    data = call(
        "POST",
        f"{base_url}/api/token/",
        data={"username": username, "password": password},
    )
    return data["token"]


def describe(save):
    """One line summarising a save, e.g. 'Dune (OL893414W) - read, 5/5'."""
    book = save["book"]
    rating = f"{save['rating']}/5" if save["rating"] is not None else "not rated"
    return f"{book['title']} ({book['work_id']}) - {save['status']}, {rating}"


def show(label, data):
    print(f"\n{label}")
    print(json.dumps(data, indent=2))


def list_public_saves(args):
    """GET /api/users/<username>/saved-books/?page=N (no sign-in needed)."""
    url = f"{args.base_url}/api/users/{args.username}/saved-books/"
    data = call("GET", url, params={"page": args.page})

    print(f"GET {url}?page={args.page}")
    print(f"{data['count']} public save(s) for {args.username}:")
    for save in data["results"]:
        print(f"  - {describe(save)}")
    print(f"Previous page: {data['previous'] or 'none'}")
    print(f"Next page:     {data['next'] or 'none'}")
    if args.verbose:
        show("Full response:", data)


def update_rating(args):
    """PATCH /api/saved-books/<id>/ with a new rating, showing before and after."""
    password = (
        args.password
        or os.environ.get("BOOK_API_PASSWORD")
        or getpass.getpass(f"Password for {args.username}: ")
    )
    token = get_token(args.base_url, args.username, password)

    save_id = args.save_id
    if save_id is None:
        # Default to the newest of the user's own saves.
        saves = call("GET", f"{args.base_url}/api/saved-books/", token=token)
        if not saves["results"]:
            raise ApiError(f"{args.username} has no saved books to update.")
        save_id = saves["results"][0]["id"]

    url = f"{args.base_url}/api/saved-books/{save_id}/"
    before = call("GET", url, token=token)
    after = call("PATCH", url, token=token, json={"rating": args.rating})

    print(f"PATCH {url}  {{'rating': {args.rating}}}")
    print(f"Before: {describe(before)}")
    print(f"After:  {describe(after)}")
    show("Before (full JSON):", before)
    show("After (full JSON):", after)


def rating(value):
    number = int(value)
    if not 1 <= number <= 5:
        raise argparse.ArgumentTypeError("rating must be 1-5")
    return number


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BOOK_API_URL", DEFAULT_BASE_URL),
        help=f"API server (default: $BOOK_API_URL or {DEFAULT_BASE_URL})",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    list_cmd = commands.add_parser("list", help="list a user's public saves")
    list_cmd.add_argument("username")
    list_cmd.add_argument("--page", type=int, default=1, help="page number")
    list_cmd.add_argument(
        "--verbose", action="store_true", help="also print the full JSON"
    )
    list_cmd.set_defaults(handler=list_public_saves)

    update_cmd = commands.add_parser("update", help="change one save's rating")
    update_cmd.add_argument("--username", required=True)
    update_cmd.add_argument("--password", help="default: $BOOK_API_PASSWORD")
    update_cmd.add_argument("--rating", type=rating, required=True, help="1-5")
    update_cmd.add_argument(
        "--save-id", type=int, help="save to update (default: your newest)"
    )
    update_cmd.set_defaults(handler=update_rating)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.base_url = args.base_url.rstrip("/")
    try:
        args.handler(args)
    except ApiError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
