import os
import sys
from pathlib import Path

# Add CORE API key to environment
os.environ['CORE_API_KEY'] = 'pvJ3MjDf9HCgYS4luTaNtbnQ072BsGK8'

# Test imports
print("Testing imports...")
from fetcher import search_arxiv, search_semantic_scholar, search_core, search_pubmed, unified_search

print("\n=== Testing ArXiv ===")
try:
    papers = search_arxiv("transformer neural networks", max_results=2)
    print(f"[OK] ArXiv: Found {len(papers)} papers")
    if papers:
        print(f"  Sample: {papers[0].title[:60]}...")
        print(f"  PDF URL: {papers[0].pdf_url}")
except Exception as e:
    print(f"[FAIL] ArXiv failed: {e}")

print("\n=== Testing Semantic Scholar ===")
try:
    papers = search_semantic_scholar("machine learning", max_results=2)
    print(f"[OK] Semantic Scholar: Found {len(papers)} papers")
    if papers:
        print(f"  Sample: {papers[0].title[:60]}...")
        print(f"  PDF URL: {papers[0].pdf_url}")
except Exception as e:
    print(f"[FAIL] Semantic Scholar failed: {e}")

print("\n=== Testing CORE ===")
try:
    papers = search_core("deep learning", max_results=2)
    print(f"[OK] CORE: Found {len(papers)} papers")
    if papers:
        print(f"  Sample: {papers[0].title[:60]}...")
        print(f"  PDF URL: {papers[0].pdf_url}")
except Exception as e:
    print(f"[FAIL] CORE failed: {e}")

print("\n=== Testing PubMed ===")
try:
    papers = search_pubmed("cancer treatment", max_results=2)
    print(f"[OK] PubMed: Found {len(papers)} papers")
    if papers:
        print(f"  Sample: {papers[0].title[:60]}...")
        print(f"  PDF URL: {papers[0].pdf_url}")
except Exception as e:
    print(f"[FAIL] PubMed failed: {e}")

print("\n=== Testing Unified Search ===")
try:
    papers = unified_search("neural networks", max_results=5)
    print(f"[OK] Unified Search: Found {len(papers)} unique papers")
    for i, paper in enumerate(papers[:3], 1):
        print(f"  {i}. {paper.title[:60]}...")
except Exception as e:
    print(f"[FAIL] Unified Search failed: {e}")

print("\n=== All Tests Complete ===")
