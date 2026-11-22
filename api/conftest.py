import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def no_https_redirect_in_tests(settings):
    # The test client talks plain HTTP, so never redirect to HTTPS while testing.
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture(autouse=True)
def clear_cache():
    # Rate limits remember requests in the cache, so every test starts clean.
    cache.clear()