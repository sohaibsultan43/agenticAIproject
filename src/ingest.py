"""
ScholarSync - Ingestion Module
===============================
This module handles PDF ingestion, embedding generation, and Weaviate storage.

Phase 3: The Analyst (Ingestion & RAG)
- Reads PDFs using LlamaParse (better equation/table extraction)
- Splits text into hierarchical chunks (parent-child structure)
- Generates embeddings using Weaviate's built-in vectorizer
- Stores vectors in Weaviate with batch insertion for speed
- Uses AutoMergingRetriever for intelligent context retrieval
"""

import os
import weaviate
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import asyncio
from dotenv import load_dotenv

from .logging_utils import setup_logging
import logging

import google.generativeai as genai
from llama_index.core import (
    Document,
    VectorStoreIndex,
    StorageContext,
    Settings
)
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.schema import TextNode
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from llama_index.readers.file import PyMuPDFReader

# Load environment variables
load_dotenv()
setup_logging("ScholarSync")
logger = logging.getLogger("ScholarSync.ingest")

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WEAVIATE_CLOUD_URL = os.getenv("WEAVIATE_CLOUD_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloaded_papers"))

# Weaviate class name for storing research papers
WEAVIATE_CLASS_NAME = "ResearchPaper"

# Hierarchical chunk sizes for research papers
# Large: Full sections/abstracts, Medium: Paragraphs, Small: Sentences
# Increased smallest size from 128->256 to avoid equation fragments
HIERARCHICAL_CHUNK_SIZES = [2048, 512, 256]

# Batch size for Weaviate insertion (for speed)
BATCH_SIZE = 100


def configure_gemini():
    """Configure the Gemini API with the provided API key."""
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_google_api_key_here":
        raise ValueError(
            "Please set your GOOGLE_API_KEY in the .env file.\n"
            "Get your key from: https://aistudio.google.com/app/apikey"
        )
    genai.configure(api_key=GOOGLE_API_KEY)


def get_weaviate_client() -> weaviate.WeaviateClient:
    """
    Create and return a Weaviate Cloud client connection.
    
    Returns:
        Connected Weaviate client
    """
    import weaviate.classes.init as wc_init
    
    if not WEAVIATE_CLOUD_URL or WEAVIATE_CLOUD_URL == "your_weaviate_cloud_url_here":
        raise ValueError(
            "Please set your WEAVIATE_CLOUD_URL in the .env file.\n"
            "Get your credentials from: https://console.weaviate.cloud/"
        )
    
    if not WEAVIATE_API_KEY or WEAVIATE_API_KEY == "your_weaviate_api_key_here":
        raise ValueError(
            "Please set your WEAVIATE_API_KEY in the .env file.\n"
            "Get your credentials from: https://console.weaviate.cloud/"
        )
    
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_CLOUD_URL,
        auth_credentials=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY),
        additional_config=wc_init.AdditionalConfig(
            timeout=wc_init.Timeout(init=30, query=60, insert=120)
        ),
        skip_init_checks=True
    )
    return client


def create_weaviate_schema(client: weaviate.WeaviateClient) -> None:
    """
    Create the Weaviate schema for storing hierarchical research paper chunks.
    
    The schema supports parent-child relationships between chunks:
    - node_id: Unique identifier for each node
    - parent_id: Reference to parent node (empty for root nodes)
    - node_level: Hierarchy level (0=large/parent, 1=medium, 2=small/leaf)
    
    Args:
        client: Connected Weaviate client
    """
    # Check if class already exists
    if client.collections.exists(WEAVIATE_CLASS_NAME):
        logger.info("Weaviate collection exists: %s", WEAVIATE_CLASS_NAME)
        # Ensure tenant_id property exists
        collection = client.collections.get(WEAVIATE_CLASS_NAME)
        existing_props = {p.name for p in collection.config.get().properties}
        if "tenant_id" not in existing_props:
            collection.config.add_property(
                weaviate.classes.config.Property(
                    name="tenant_id",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Session/tenant id",
                    skip_vectorization=True,
                )
            )
        return
    
    # Create the collection with Weaviate's built-in vectorizer
    # This uses Weaviate's embedding model instead of external API
    client.collections.create(
        name=WEAVIATE_CLASS_NAME,
        properties=[
            weaviate.classes.config.Property(
                name="text",
                data_type=weaviate.classes.config.DataType.TEXT,
                description="The text content of the chunk"
            ),
            weaviate.classes.config.Property(
                name="node_id",
                data_type=weaviate.classes.config.DataType.TEXT,
                description="Unique identifier for this node",
                skip_vectorization=True
            ),
            weaviate.classes.config.Property(
                name="parent_id",
                data_type=weaviate.classes.config.DataType.TEXT,
                description="ID of the parent node (empty for root nodes)",
                skip_vectorization=True
            ),
            weaviate.classes.config.Property(
                name="node_level",
                data_type=weaviate.classes.config.DataType.INT,
                description="Hierarchy level: 0=large, 1=medium, 2=leaf",
                skip_vectorization=True
            ),
            weaviate.classes.config.Property(
                name="filename",
                data_type=weaviate.classes.config.DataType.TEXT,
                description="Source PDF filename",
                skip_vectorization=True
            ),
            weaviate.classes.config.Property(
                name="page_number",
                data_type=weaviate.classes.config.DataType.INT,
                description="Page number in the PDF",
                skip_vectorization=True
            ),
            weaviate.classes.config.Property(
                name="creation_date",
                data_type=weaviate.classes.config.DataType.TEXT,
                description="Date when the document was ingested",
                skip_vectorization=True
            ),
            weaviate.classes.config.Property(
                name="tenant_id",
                data_type=weaviate.classes.config.DataType.TEXT,
                description="Session/tenant id",
                skip_vectorization=True
            ),
        ],
        vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_weaviate(),
    )
    logger.info("Created Weaviate collection: %s", WEAVIATE_CLASS_NAME)


def setup_llama_index() -> tuple:
    """
    Configure LlamaIndex with Gemini embeddings and LLM.
    
    Returns:
        Tuple of (embed_model, llm)
    """
    configure_gemini()
    
    # Initialize Gemini embedding model
    embed_model = GeminiEmbedding(
        model_name="models/gemini-embedding-001",
        api_key=GOOGLE_API_KEY
    )
    
    # Initialize Gemini LLM
    llm = Gemini(
        model="models/gemini-2.5-flash",
        api_key=GOOGLE_API_KEY
    )
    
    # Configure global settings
    Settings.embed_model = embed_model
    Settings.llm = llm
    Settings.chunk_size = 1024
    Settings.chunk_overlap = 200
    
    return embed_model, llm


def load_pdfs(pdf_dir: Path = DOWNLOAD_DIR, specific_files: List[Path] = None) -> List[Document]:
    """
    Load PDFs from the specified directory or list using LlamaParse or PyMuPDF.
    
    Args:
        pdf_dir: Directory containing PDF files (used if specific_files is None)
        specific_files: Optional list of specific file paths to load
        
    Returns:
        List of Document objects
    """
    if specific_files:
        pdf_files = [Path(f) for f in specific_files if Path(f).exists()]
        logger.info("Loading PDFs (specific files): %d", len(pdf_files))
    else:
        pdf_dir = Path(pdf_dir)
        pdf_files = list(pdf_dir.glob("*.pdf"))
        logger.info("Loading PDFs from folder: %s (%d)", str(pdf_dir), len(pdf_files))
    
    if not pdf_files:
        logger.warning("No PDF files found to process")
        return []
    
    logger.info("PDF files to process: %d", len(pdf_files))
    
    all_documents = []
    
    # Try LlamaParse first for better equation/table extraction
    if LLAMA_CLOUD_API_KEY and LLAMA_CLOUD_API_KEY != "your_llama_cloud_api_key_here":
        try:
            from llama_parse import LlamaParse
            
            logger.info("Parsing PDFs with LlamaParse")
            
            parser = LlamaParse(
                api_key=LLAMA_CLOUD_API_KEY,
                result_type="markdown",  # Better for equations and tables
                # parsing_instruction is deprecated; use system_prompt to avoid warnings/noise
                system_prompt="Extract all text, equations (as LaTeX), and tables from this academic research paper. Preserve mathematical notation.",
                verbose=False
            )
            
            for pdf_path in pdf_files:
                logger.info("Parsing: %s", pdf_path.name)
                try:
                    # LlamaParse may rely on an event loop even when called from a thread.
                    # When `load_pdfs` is executed inside `run_in_executor`, the thread can
                    # have no loop or a closed loop; ensure a valid loop exists.
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            raise RuntimeError("Event loop is closed")
                    except Exception:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    # LlamaParse returns parsed documents
                    parsed_docs = parser.load_data(str(pdf_path))
                    
                    # Convert to LlamaIndex Documents with metadata
                    for i, doc in enumerate(parsed_docs):
                        llama_doc = Document(
                            text=doc.text,
                            metadata={
                                "filename": pdf_path.name,
                                "page": i + 1,
                                "creation_date": datetime.now().isoformat(),
                                "parser": "llamaparse"
                            }
                        )
                        all_documents.append(llama_doc)
                    
                    logger.debug("Parsed sections: %d", len(parsed_docs))
                    
                except Exception as e:
                    logger.warning("LlamaParse failed for %s; falling back to PyMuPDF. Error: %s", pdf_path.name, str(e))
                    # Fallback to PyMuPDF for this file
                    all_documents.extend(_load_pdf_with_pymupdf(pdf_path))
            
            logger.info("Documents loaded: %d", len(all_documents))
            return all_documents
            
        except ImportError:
            logger.warning("llama-parse not installed. Falling back to PyMuPDF.")
    else:
        logger.info("LLAMA_CLOUD_API_KEY not set. Using PyMuPDF parser.")
    
    # Fallback: Use PyMuPDF
    for pdf_path in pdf_files:
        all_documents.extend(_load_pdf_with_pymupdf(pdf_path))
    
    logger.info("Documents loaded: %d", len(all_documents))
    return all_documents


def _load_pdf_with_pymupdf(pdf_path: Path) -> List[Document]:
    """Load a single PDF using PyMuPDF (fallback parser)."""
    logger.info("Loading: %s", pdf_path.name)
    pdf_reader = PyMuPDFReader()
    documents = []
    
    try:
        docs = pdf_reader.load(file_path=str(pdf_path))
        
        for doc in docs:
            doc.metadata["filename"] = pdf_path.name
            doc.metadata["creation_date"] = datetime.now().isoformat()
            doc.metadata["parser"] = "pymupdf"
        
        documents.extend(docs)
        logger.debug("Loaded pages: %d", len(docs))
        
    except Exception as e:
        logger.warning("Error loading %s: %s", pdf_path.name, str(e))
    
    return documents


def create_vector_index(
    documents: List[Document],
    client: weaviate.WeaviateClient,
    tenant_id: str = "default"
) -> dict:
    """
    Insert documents into Weaviate using hierarchical chunking.
    
    Creates a parent-child node structure:
    - Level 0: Large chunks (2048 chars) - full sections
    - Level 1: Medium chunks (512 chars) - paragraphs  
    - Level 2: Leaf chunks (128 chars) - precise retrieval targets
    
    Weaviate handles vectorization automatically.
    
    Args:
        documents: List of Document objects to index
        client: Connected Weaviate client
        
    Returns:
        Dictionary with counts: {total_nodes, leaf_nodes, parent_nodes}
    """
    # Keep output readable: no emojis and no noisy per-step prints.
    # Only key indicators at INFO; details at DEBUG.
    logger.info("Indexing into Weaviate (tenant=%s)", tenant_id)
    logger.debug("Chunk sizes=%s batch_size=%d", HIERARCHICAL_CHUNK_SIZES, BATCH_SIZE)
    
    # Get the collection
    collection = client.collections.get(WEAVIATE_CLASS_NAME)
    
    # Configure Hierarchical Node Parser for research papers
    # Creates multi-level chunks: large → medium → small (leaf)
    node_parser = HierarchicalNodeParser.from_defaults(
        chunk_sizes=HIERARCHICAL_CHUNK_SIZES
    )
    
    # Parse documents into hierarchical nodes
    logger.debug("Building hierarchical nodes...")
    all_nodes = node_parser.get_nodes_from_documents(documents)
    
    # Separate leaf nodes from parent nodes
    leaf_nodes = get_leaf_nodes(all_nodes)
    parent_nodes = [n for n in all_nodes if n not in leaf_nodes]
    
    logger.info("Nodes: total=%d leaf=%d parent=%d", len(all_nodes), len(leaf_nodes), len(parent_nodes))
    
    # Build a map of node relationships
    node_to_level = {}
    for node in all_nodes:
        # Determine level based on text length (approximate)
        text_len = len(node.text) if hasattr(node, 'text') else 0
        if text_len > 1500:
            node_to_level[node.node_id] = 0  # Large/parent
        elif text_len > 300:
            node_to_level[node.node_id] = 1  # Medium
        else:
            node_to_level[node.node_id] = 2  # Small/leaf
    
    # Prepare all node data for batch insertion
    logger.debug("Preparing batch objects...")
    node_data_list = []
    
    for node in all_nodes:
        # Get node text and metadata
        node_text = node.text if hasattr(node, 'text') else str(node)
        node_id = node.node_id if hasattr(node, 'node_id') else str(len(node_data_list))
        
        # Get parent ID if exists
        parent_id = ""
        if hasattr(node, 'relationships'):
            for rel_type, rel_info in node.relationships.items():
                if 'PARENT' in str(rel_type).upper():
                    parent_id = rel_info.node_id if hasattr(rel_info, 'node_id') else str(rel_info)
                    break
        
        # Get metadata from original document
        metadata = node.metadata if hasattr(node, 'metadata') else {}
        
        node_data_list.append({
            "text": node_text,
            "node_id": node_id,
            "parent_id": parent_id,
            "node_level": node_to_level.get(node_id, 2),
            "filename": metadata.get("filename", "unknown"),
            "page_number": metadata.get("page", 0),
            "creation_date": metadata.get("creation_date", datetime.now().isoformat()),
            "tenant_id": tenant_id,
        })
    
    # Batch insert for speed (10-20x faster than one-by-one)
    logger.info("Inserting nodes: %d", len(node_data_list))
    nodes_inserted = 0
    
    with collection.batch.dynamic() as batch:
        for i, node_data in enumerate(node_data_list):
            batch.add_object(properties=node_data)
            nodes_inserted += 1
            
            # Progress update every 100 nodes
            if (i + 1) % 100 == 0:
                logger.debug("Insert progress: %d/%d", i + 1, len(node_data_list))
    
    logger.info("Inserted nodes: %d", nodes_inserted)
    
    return {
        "total_nodes": nodes_inserted,
        "leaf_nodes": len(leaf_nodes),
        "parent_nodes": len(parent_nodes)
    }


def get_existing_index(client: weaviate.WeaviateClient) -> Optional[VectorStoreIndex]:
    """
    Load an existing index from Weaviate.
    
    Args:
        client: Connected Weaviate client
        
    Returns:
        VectorStoreIndex if exists, None otherwise
    """
    if not client.collections.exists(WEAVIATE_CLASS_NAME):
        return None
    
    vector_store = WeaviateVectorStore(
        weaviate_client=client,
        index_name=WEAVIATE_CLASS_NAME,
        text_key="text"
    )
    
    index = VectorStoreIndex.from_vector_store(vector_store)
    return index


def ingest_papers(pdf_dir: Path = DOWNLOAD_DIR) -> VectorStoreIndex:
    """
    Main function to ingest all papers from a directory.
    
    Args:
        pdf_dir: Directory containing PDF files
        
    Returns:
        Number of chunks ingested
    """
    logger.info("Starting ingestion")
    
    # Connect to Weaviate
    logger.info("Connecting to Weaviate...")
    client = get_weaviate_client()
    logger.info("Connected to Weaviate Cloud")
    
    # Create schema
    logger.info("Ensuring schema...")
    create_weaviate_schema(client)
    
    # Load PDFs
    logger.info("Loading PDF documents...")
    documents = load_pdfs(pdf_dir)
    
    if not documents:
        client.close()
        return None
    
    # Insert documents into Weaviate (Weaviate handles embeddings)
    logger.info("Indexing documents...")
    _ = create_vector_index(documents, client)
    
    # Verify storage
    collection = client.collections.get(WEAVIATE_CLASS_NAME)
    count = collection.aggregate.over_all(total_count=True).total_count
    logger.info("Total chunks stored: %d", count)
    
    client.close()
    
    logger.info("Ingestion complete")
    
    return count


def query_papers(question: str, top_k: int = 8, merge_threshold: int = 2) -> str:
    """
    Query the ingested papers using hierarchical auto-merging retrieval.
    
    When multiple leaf nodes from the same parent are retrieved, they are 
    merged with their parent to provide more coherent context.
    
    Args:
        question: The question to ask
        top_k: Number of relevant chunks to retrieve
        merge_threshold: If this many children share a parent, use parent instead
        
    Returns:
        Answer from the RAG system
    """
    import weaviate.classes.query as wq
    
    # Connect to Weaviate
    client = get_weaviate_client()
    
    # Check if collection exists
    if not client.collections.exists(WEAVIATE_CLASS_NAME):
        client.close()
        return "No papers have been ingested yet. Please run ingestion first."
    
    # Get collection
    collection = client.collections.get(WEAVIATE_CLASS_NAME)
    
    # Perform near_text search on leaf nodes first (most precise)
    results = collection.query.near_text(
        query=question,
        limit=top_k,
        return_metadata=wq.MetadataQuery(distance=True),
        filters=wq.Filter.by_property("tenant_id").equal("default")
    )
    
    if not results.objects:
        client.close()
        return "No relevant information found in the ingested papers."
    
    # Implement auto-merging: if multiple children share a parent, use parent
    parent_children = {}  # parent_id -> list of child objects
    orphan_nodes = []  # nodes without parents
    
    for obj in results.objects:
        parent_id = obj.properties.get("parent_id", "")
        if parent_id:
            if parent_id not in parent_children:
                parent_children[parent_id] = []
            parent_children[parent_id].append(obj)
        else:
            orphan_nodes.append(obj)
    
    # Build context, merging children to parent when threshold met
    context_parts = []
    sources = set()
    used_parents = set()
    
    for parent_id, children in parent_children.items():
        if len(children) >= merge_threshold and parent_id not in used_parents:
            # Fetch parent node for better context
            parent_results = collection.query.fetch_objects(
                filters=wq.Filter.by_property("node_id").equal(parent_id),
                limit=1
            )
            
            if parent_results.objects:
                parent_obj = parent_results.objects[0]
                text = parent_obj.properties.get("text", "")
                filename = parent_obj.properties.get("filename", "unknown")
                page = parent_obj.properties.get("page_number", 0)
                
                context_parts.append(
                    f"[Merged Context from {len(children)} matches] "
                    f"(Source: {filename}, Page: {page})\n{text}"
                )
                sources.add(filename)
                used_parents.add(parent_id)
            else:
                # Fallback: use children directly
                for child in children:
                    text = child.properties.get("text", "")
                    filename = child.properties.get("filename", "unknown")
                    page = child.properties.get("page_number", 0)
                    context_parts.append(f"(Source: {filename}, Page: {page})\n{text}")
                    sources.add(filename)
        else:
            # Use children directly if below threshold
            for child in children:
                text = child.properties.get("text", "")
                filename = child.properties.get("filename", "unknown")
                page = child.properties.get("page_number", 0)
                context_parts.append(f"(Source: {filename}, Page: {page})\n{text}")
                sources.add(filename)
    
    # Add orphan nodes (no parent)
    for obj in orphan_nodes:
        text = obj.properties.get("text", "")
        filename = obj.properties.get("filename", "unknown")
        page = obj.properties.get("page_number", 0)
        context_parts.append(f"(Source: {filename}, Page: {page})\n{text}")
        sources.add(filename)
    
    context = "\n\n---\n\n".join(context_parts)
    
    client.close()
    
    # Use Gemini to generate answer based on context
    configure_gemini()
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction="""You are a research analyst. Provide well-structured responses based on academic paper content.

Response Guidelines:
- Use markdown formatting with headers and bullet points
- Cite sources in the format: (Source: filename)
- Be precise and factual
- Group related information under subheadings when appropriate
- If information is not available, state this clearly"""
    )
    
    prompt = f"""Context from research papers (using hierarchical retrieval):

{context}

---

Question: {question}

Provide a structured response based on the context above."""
    
    response = model.generate_content(prompt)
    
    # Add sources footer
    source_list = ", ".join(sources)
    answer = f"{response.text}\n\nSources: {source_list}"
    
    return answer


# CLI Interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        # Query mode
        if len(sys.argv) > 2:
            question = " ".join(sys.argv[2:])
        else:
            question = "What are the main findings in these papers?"
        
        print(f"\nQuestion: {question}\n")
        answer = query_papers(question)
        print(f"Answer:\n{answer}")
    else:
        # Ingest mode
        ingest_papers()
