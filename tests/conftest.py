import sys
import os
import pytest

# Ensure project root and web directory are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if WEB_DIR not in sys.path:
    sys.path.insert(0, WEB_DIR)

from app import app
from services.database import get_db_connection, DB_PATH

@pytest.fixture(scope="session")
def flask_app():
    app.config["TESTING"] = True
    return app

@pytest.fixture(scope="function")
def client(flask_app):
    return flask_app.test_client()

@pytest.fixture(scope="function")
def db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
