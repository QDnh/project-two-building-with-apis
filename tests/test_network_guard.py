"""The autouse `block_network` fixture (tests/conftest.py) is itself tested here."""

import socket
import urllib.request

import pytest
import requests

import openlibrary_search as ols


def test_unfaked_requests_call_fails_the_test():
    with pytest.raises(pytest.fail.Exception, match="real network connection"):
        requests.get("https://openlibrary.org/search.json", timeout=1)


def test_unfaked_urllib_call_fails_the_test():
    with pytest.raises(pytest.fail.Exception, match="real network connection"):
        urllib.request.urlopen("https://openlibrary.org/search.json", timeout=1)


def test_raw_socket_connection_fails_the_test():
    with socket.socket() as sock, pytest.raises(pytest.fail.Exception):
        sock.connect(("93.184.216.34", 443))


def test_open_library_client_cannot_hide_the_failure_as_a_search_error():
    # The client turns network errors into SearchError. The guard must not be
    # swallowed that way, or a test could pass while hitting the real API.
    with pytest.raises(pytest.fail.Exception):
        ols.search_books("dune")
