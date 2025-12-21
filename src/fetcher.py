"""
ScholarSync - Fetcher Module
=============================
This module handles searching ArXiv and downloading research papers.

Phase 2: The Fetcher (Autonomous Agent)
- Searches ArXiv API with refined queries
- Downloads PDFs to local storage
- Sanitizes filenames for safe storage
"""

import os
import re
import arxiv
import requests
from pathlib import Path
from typing import List, Optional
from datetime import datetime, date
from dataclasses import dataclass
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

# Load environment variables
load_dotenv()

# Configuration
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloaded_papers"))
MAX_PAPERS = int(os.getenv("MAX_PAPERS_PER_SEARCH", 10))

logger = logging.getLogger("ScholarSync.fetcher")
SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


@dataclass
class PaperInfo:
    """Data class to store paper metadata."""
    title: str
    authors: List[str]
    abstract: str
    arxiv_id: str
    pdf_url: str
    published: str
    categories: List[str]
    local_path: Optional[str] = None


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """
    Convert a paper title into a safe filename.
    
    Args:
        title: The original paper title
        max_length: Maximum length for the filename
        
    Returns:
        A sanitized filename string
    """
    # Remove special characters and replace spaces with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'[^\w\-_.]', '', sanitized)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    # Remove trailing underscores and add extension
    sanitized = sanitized.rstrip('_')
    
    return f"{sanitized}.pdf"


def _parse_iso_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    try:
        return date.fromisoformat(d.strip())
    except Exception:
        return None


def search_arxiv(
    query: str,
    max_results: int = MAX_PAPERS,
    author: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_scan: int = 200,
) -> List[PaperInfo]:
    """
    Search ArXiv for papers matching the query.
    
    Args:
        query: The search query string
        max_results: Maximum number of papers to retrieve
        
    Returns:
        List of PaperInfo objects
    """
    logger.info("ArXiv search | query=%r", query)
    
    # Configure the ArXiv search
    # NOTE: We intentionally fetch more than requested and then filter locally.
    # This avoids relying on ArXiv query syntax for date/author and keeps behavior predictable.
    scan_limit = min(max(max_results * 5, max_results), max_scan)
    search = arxiv.Search(
        query=query,
        max_results=scan_limit,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending
    )
    
    papers = []
    client = arxiv.Client()
    
    author_norm = (author or "").strip().lower()
    start_d = _parse_iso_date(start_date)
    end_d = _parse_iso_date(end_date)

    for result in client.results(search):
        published_dt = result.published  # datetime
        published_str = published_dt.strftime("%Y-%m-%d")

        # --- Local filters ---
        if author_norm:
            result_authors = [a.name for a in result.authors]
            if not any(author_norm in a.lower() for a in result_authors):
                continue

        if start_d or end_d:
            pub_date = published_dt.date() if isinstance(published_dt, datetime) else None
            if pub_date is None:
                continue
            if start_d and pub_date < start_d:
                continue
            if end_d and pub_date > end_d:
                continue

        paper = PaperInfo(
            title=result.title,
            authors=[author.name for author in result.authors],
            abstract=result.summary,
            arxiv_id=result.entry_id.split('/')[-1],
            pdf_url=result.pdf_url,
            published=published_str,
            categories=result.categories
        )
        papers.append(paper)
        logger.debug("ArXiv result: %s", paper.title[:80])

        # Stop early once we have the requested amount after filtering
        if len(papers) >= max_results:
            break
    
    logger.info("ArXiv search done | results=%d", len(papers))
    return papers


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
def search_semantic_scholar(
    query: str,
    max_results: int = 20,
    author: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[PaperInfo]:
    """
    Search Semantic Scholar for papers matching the query.

    Notes:
    - We only return papers with an open-access PDF URL (so download works).
    - Filters are applied locally for predictability.
    """
    author_norm = (author or "").strip().lower()
    start_d = _parse_iso_date(start_date)
    end_d = _parse_iso_date(end_date)
    start_year = start_d.year if start_d else None
    end_year = end_d.year if end_d else None

    # Fetch more than needed; many results won't have openAccessPdf
    fetch_limit = min(max(max_results * 4, max_results), 100)
    params = {
        "query": query,
        "limit": fetch_limit,
        "fields": "title,authors,year,abstract,openAccessPdf,url",
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "ScholarSync/1.0",
    }

    try:
        resp = requests.get(SEMANTIC_SCHOLAR_SEARCH_URL, params=params, headers=headers, timeout=30)
        if resp.status_code == 429:
            raise RuntimeError("Semantic Scholar rate limited (429). Please wait ~30-60s and try again.")
        resp.raise_for_status()
        data = resp.json() or {}
    except Exception as e:
        raise RuntimeError(f"Semantic Scholar search failed: {e}") from e

    results = []
    for item in (data.get("data") or []):
        title = (item.get("title") or "").strip()
        if not title:
            continue

        authors_list = [a.get("name", "").strip() for a in (item.get("authors") or [])]
        authors_list = [a for a in authors_list if a]
        if author_norm and not any(author_norm in a.lower() for a in authors_list):
            continue

        year = item.get("year")
        if isinstance(year, int):
            if start_year and year < start_year:
                continue
            if end_year and year > end_year:
                continue
            published = str(year)
        else:
            published = ""

        abstract = (item.get("abstract") or "").strip()

        oa = item.get("openAccessPdf") or {}
        pdf_url = (oa.get("url") or "").strip()
        if not pdf_url:
            # Skip papers without a PDF we can download
            continue

        # Prefer stable ID if present; otherwise fall back to Semantic Scholar URL
        paper_id = (item.get("paperId") or item.get("url") or title)[:200]

        results.append(
            PaperInfo(
                title=title,
                authors=authors_list,
                abstract=abstract,
                arxiv_id=paper_id,
                pdf_url=pdf_url,
                published=published,
                categories=[],
            )
        )
        if len(results) >= max_results:
            break

    logger.info("Semantic Scholar results: %s (query=%r)", len(results), query)
    return results


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def download_pdf(paper: PaperInfo, download_dir: Path = DOWNLOAD_DIR) -> Optional[str]:
    """
    Download a PDF from ArXiv with retry logic.
    
    Args:
        paper: PaperInfo object containing paper details
        download_dir: Directory to save the PDF
        
    Returns:
        Path to the downloaded file, or None if failed
    """
    # Ensure download directory exists
    download_dir.mkdir(parents=True, exist_ok=True)
    
    # Create safe filename
    filename = sanitize_filename(paper.title)
    filepath = download_dir / filename
    
    # Skip if already downloaded
    if filepath.exists():
        logger.info("Download skipped (exists) | file=%s", filename)
        paper.local_path = str(filepath)
        return str(filepath)
    
    logger.info("Downloading | file=%s", filename)
    
    try:
        # Download the PDF
        response = requests.get(paper.pdf_url, timeout=60)
        response.raise_for_status()
        
        # Save to file
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        paper.local_path = str(filepath)
        logger.info("Downloaded | file=%s", filename)
        return str(filepath)
        
    except requests.RequestException as e:
        logger.warning("Download failed | title=%r error=%s", paper.title, str(e))
        return None


def fetch_papers(query: str, max_results: int = MAX_PAPERS) -> List[PaperInfo]:
    """
    Main function to search and download papers from ArXiv.
    
    Args:
        query: The search query string
        max_results: Maximum number of papers to download
        
    Returns:
        List of PaperInfo objects with local_path populated for downloaded files
    """
    # Search for papers
    papers = search_arxiv(query, max_results)
    
    if not papers:
        print("❌ No papers found for the query")
        return []
    
    # Download each paper
    print(f"\n📥 Downloading {len(papers)} papers...")
    successful_downloads = 0
    
    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] {paper.title[:50]}...")
        if download_pdf(paper):
            successful_downloads += 1
    
    print(f"\n🎉 Successfully downloaded {successful_downloads}/{len(papers)} papers")
    print(f"📁 Papers saved to: {DOWNLOAD_DIR.absolute()}")
    
    return papers


def get_downloaded_papers() -> List[Path]:
    """
    Get a list of all downloaded PDF files (including subfolders).
    
    Returns:
        List of Path objects for each PDF
    """
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Use recursive glob to find PDFs in subfolders too
    return list(DOWNLOAD_DIR.glob("**/*.pdf"))


# CLI Interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # Default test query
        query = "Quantum Computing"
    
    print("=" * 60)
    print("ScholarSync - Paper Fetcher")
    print("=" * 60)
    
    papers = fetch_papers(query, max_results=3)
    
    print("\n" + "=" * 60)
    print("Downloaded Papers Summary:")
    print("=" * 60)
    
    for paper in papers:
        if paper.local_path:
            print(f"\n📄 {paper.title}")
            print(f"   Authors: {', '.join(paper.authors[:3])}")
            print(f"   Published: {paper.published}")
            print(f"   File: {paper.local_path}")
