# Proxy module to make `from app import app, db` work when running tests from repo root.
from asta_authentication.app import app  # noqa: F401
from asta_authentication.models import db  # noqa: F401
