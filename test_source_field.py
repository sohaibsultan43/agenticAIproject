import os
import sys

# Add CORE API key
os.environ['CORE_API_KEY'] = 'pvJ3MjDf9HCgYS4luTaNtbnQ072BsGK8'

# Test that source field is being set
from fetcher import unified_search

print("Testing unified search with source tracking...")
papers = unified_search("machine learning", max_results=3, sources=["arxiv", "semantic_scholar"])

print(f"\nFound {len(papers)} papers:\n")
for i, paper in enumerate(papers, 1):
    print(f"{i}. {paper.title[:50]}...")
    print(f"   Source: {paper.source}")
    print(f"   PDF: {paper.pdf_url[:50]}...")
    print()

print("Test complete!")
