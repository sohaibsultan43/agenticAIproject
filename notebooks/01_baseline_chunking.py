"""
Baseline Experimentation: Document Chunking and Embedding Process

This notebook demonstrates how ScholarSync processes academic papers into chunks,
embeds them, and stores them in the Weaviate vector database.
"""

# %%
import sys
sys.path.append('..')

from pathlib import Path
import json
from src.ingest import load_pdfs, get_weaviate_client, create_weaviate_schema, WEAVIATE_CLASS_NAME
from src.fetcher import search_arxiv, download_pdf
import weaviate.classes.query as wq

# %% [markdown]
## 1. Sample Paper Selection
# 
# Let's use a sample paper to demonstrate the chunking process.
# For this experiment, we'll use a well-known paper on transformers.

# %%
# Search for a sample paper
print("Searching for sample paper...")
query = "attention is all you need"
papers = search_arxiv(query, max_results=1)

if papers:
    paper = papers[0]
    print(f"Found paper: {paper.title}")
    print(f"Authors: {', '.join(paper.authors)}")
    print(f"Published: {paper.published}")
    print(f"\\nAbstract:\\n{paper.abstract[:300]}...")
else:
    print("No papers found")

# %% [markdown]
## 2. Download the Paper
#
# Download the PDF to our experiment directory

# %%
experiment_dir = Path("../downloaded_papers/baseline_experiment")
experiment_dir.mkdir(parents=True, exist_ok=True)

if papers:
    print(f"\\nDownloading PDF...")
    pdf_path = download_pdf(paper, download_dir=experiment_dir)
    print(f"Downloaded to: {pdf_path}")

# %% [markdown]
## 3. Load and Parse PDF
#
# The `load_pdfs` function extracts text from the PDF and prepares it for chunking

# %%
print("\\nLoading PDF...")
documents = load_pdfs(specific_files=[Path(pdf_path)])
print(f"Loaded {len(documents)} document(s)")

if documents:
    doc = documents[0]
    print(f"\\nDocument metadata:")
    print(f"  - Filename: {doc.metadata.get('filename', 'N/A')}")
    print(f"  - Page count: {doc.metadata.get('page_count', 'N/A')}")
    print(f"\\nFirst 500 characters of text:")
    print(doc.text[:500] + "...")

# %% [markdown]
## 4. Hierarchical Chunking Process
#
# ScholarSync uses hierarchical text splitting with multiple levels:
# - Level 0: Large chunks (2048 tokens) for broad context
# - Level 1: Medium chunks (512 tokens) for balanced retrieval
# - Level 2: Small chunks (128 tokens) for precise matching

# %%
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Demonstrate chunking at different levels
chunk_sizes = [
    (2048, 200, "Large"),
    (512, 50, "Medium"),  
    (128, 20, "Small")
]

all_chunks = []
for chunk_size, overlap, level_name in chunk_sizes:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\\n\\n", "\\n", ". ", " ", ""]
    )
    
    if documents:
        chunks = splitter.split_documents(documents)
        all_chunks.append((level_name, len(chunks), chunks[:2] if chunks else []))
        print(f"\\n{level_name} chunks (size={chunk_size}, overlap={overlap}): {len(chunks)} chunks")

# %% [markdown]
## 5. Inspect Sample Chunks
#
# Let's examine the actual content of chunks at different levels

# %%
for level_name, count, sample_chunks in all_chunks:
    print(f"\\n{'='*60}")
    print(f"{level_name} Chunk Sample ({count} total chunks)")
    print(f"{'='*60}")
    
    if sample_chunks:
        chunk = sample_chunks[0]
        print(f"\\nChunk 1 content:")
        print(chunk.page_content[:400] + "..." if len(chunk.page_content) > 400 else chunk.page_content)
        print(f"\\nChunk metadata: {chunk.metadata}")

# %% [markdown]
## 6. Embedding and Vector Storage
#
# Each chunk is embedded using Gemini embeddings and stored in Weaviate

# %%
print("\\nConnecting to Weaviate...")
client = get_weaviate_client()
create_weaviate_schema(client)

# Check if collection exists
if client.collections.exists(WEAVIATE_CLASS_NAME):
    collection = client.collections.get(WEAVIATE_CLASS_NAME)
    print(f"Collection '{WEAVIATE_CLASS_NAME}' ready")
    
    # Query for chunks from our experiment
    print(f"\\nQuerying for chunks from baseline experiment...")
    results = collection.query.fetch_objects(
        filters=wq.Filter.by_property("filename").contains_any([pdf_path.name if pdf_path else ""]),
        limit=5
    )
    
    print(f"\\nFound {len(results.objects)} chunks in Weaviate")
    
    if results.objects:
        print("\\nSample chunk from Weaviate:")
        obj = results.objects[0]
        print(f"  - Text length: {len(obj.properties.get('text', ''))}")
        print(f"  - Node level: {obj.properties.get('node_level', 'N/A')}")
        print(f"  - Page number: {obj.properties.get('page_number', 'N/A')}")
        print(f"  - Filename: {obj.properties.get('filename', 'N/A')}")
        print(f"\\n  Text preview: {obj.properties.get('text', '')[:300]}...")

client.close()

# %% [markdown]
## 7. Chunk Statistics Summary
#
# Summary of the chunking process

# %%
print("\\n" + "="*60)
print("CHUNKING PROCESS SUMMARY")
print("="*60)
print(f"\\nPaper: {paper.title if papers else 'N/A'}")
print(f"\\nChunking Strategy: Hierarchical with 3 levels")
for level_name, count, _ in all_chunks:
    print(f"  - {level_name}: {count} chunks")

print(f"\\nTotal chunks created: {sum(count for _, count, _ in all_chunks)}")
print(f"\\nEmbedding Model: Gemini text-embedding-004")
print(f"Vector Database: Weaviate Cloud")
print(f"\\nAll chunks are stored with metadata including:")
print(f"  - Filename")
print(f"  - Page number")
print(f"  - Chunk level (for hierarchical retrieval)")
print(f"  - Tenant ID (for multi-user isolation)")

# %% [markdown]
## Key Insights
#
# 1. **Hierarchical Chunking**: Using multiple chunk sizes allows the system to
#    balance between broad context (large chunks) and precise matching (small chunks)
#
# 2. **Metadata Preservation**: Each chunk retains important metadata like page number
#    and filename, enabling proper citation in responses
#
# 3. **Semantic Search**: Embeddings allow finding relevant content based on meaning,
#    not just keyword matching
#
# 4. **Scalability**: The multi-tenant design allows multiple users to maintain
#    separate paper collections in the same database
