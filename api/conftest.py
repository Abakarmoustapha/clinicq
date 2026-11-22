import pytest


@pytest.fixture(autouse=True)
def no_https_redirect_in_tests(settings):
    # The test client talks plain HTTP, so never redirect to HTTPS while testing.
    settings.SECURE_SSL_REDIRECT = False