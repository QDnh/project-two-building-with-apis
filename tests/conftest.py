"""Shared test fixtures.

The network guard below runs for every test. Tests must never contact the
real Open Library: fake `requests.get` (client tests) or the client's
functions (view and API tests) instead.
"""

import socket

import pytest

# Loopback is allowed so local plumbing (e.g. an event loop's internal socket
# pair on Windows) keeps working; nothing on loopback is a real external API.
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _host_of(address):
    if isinstance(address, tuple) and address:
        return str(address[0])
    return str(address)


def _block(target):
    # pytest.fail raises an outcome exception that is not an OSError or a
    # requests exception, so code under test can't catch it and turn it into a
    # friendly "Open Library is down" message. The test fails on the spot.
    pytest.fail(
        f"Test tried to make a real network connection to {target!r}. "
        "Fake the HTTP call or the Open Library client instead.",
        pytrace=False,
    )


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Fail the test immediately if it tries to open an outgoing connection."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def guarded_connect(sock, address):
        if _host_of(address) not in LOOPBACK_HOSTS:
            _block(address)
        return real_connect(sock, address)

    def guarded_connect_ex(sock, address):
        if _host_of(address) not in LOOPBACK_HOSTS:
            _block(address)
        return real_connect_ex(sock, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host is not None and str(host) not in LOOPBACK_HOSTS:
            _block(host)
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
