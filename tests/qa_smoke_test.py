"""
QA Smoke Test for ScholarSync
- Verifies environment configuration
- Imports modules successfully
- Checks local PDF discovery
- Optionally validates Weaviate connectivity if env present
- Dry-runs key functions where feasible without external network

Run: pytest -q tests/qa_smoke_test.py
"""
import os
from pathlib import Path
import importlib
import pytest

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", ROOT / "downloaded_papers"))

REQUIRED_ENV_KEYS = [
    "GOOGLE_API_KEY",
]
OPTIONAL_ENV_KEYS = [
    "WEAVIATE_CLOUD_URL",
    "WEAVIATE_API_KEY",
]


def test_env_file_exists():
    assert ENV_PATH.exists(), f".env not found at {ENV_PATH}"


def test_required_env_keys_present():
    missing = [k for k in REQUIRED_ENV_KEYS if not os.getenv(k)]
    assert not missing, f"Missing required env keys: {missing}. Set them in .env"


def test_modules_import():
    for mod in ["app", "fetcher", "ingest"]:
        m = importlib.import_module(mod)
        assert m is not None, f"Failed to import module: {mod}"


def test_download_dir_present_and_list_pdfs():
    # Directory should exist; create if not
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    assert DOWNLOAD_DIR.exists(), f"Download dir missing: {DOWNLOAD_DIR}"
    # Listing should not error
    pdfs = list(DOWNLOAD_DIR.glob("*.pdf"))
    # It's okay if empty; just ensure Path objects
    for p in pdfs:
        assert p.exists() and p.suffix.lower() == ".pdf"


@pytest.mark.optional
@pytest.mark.skipif(not (os.getenv("WEAVIATE_CLOUD_URL") and os.getenv("WEAVIATE_API_KEY")),
                    reason="Weaviate env missing")
def test_weaviate_connectivity():
    # Uses ingest.get_weaviate_client, but does not mutate state
    ingest = importlib.import_module("ingest")
    client = ingest.get_weaviate_client()
    # simple call that should not raise
    ok = client.is_ready()
    client.close()
    assert ok is True


@pytest.mark.optional
@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="Google API key missing")
def test_gemini_configure():
    ingest = importlib.import_module("ingest")
    # Should not raise when GOOGLE_API_KEY configured properly
    ingest.configure_gemini()


@pytest.mark.optional
@pytest.mark.skip(reason="Network-dependent; enable when needed")
def test_fetcher_search_dry_run():
    # Avoid hitting arxiv/network in smoke; keep as placeholder
    pass
