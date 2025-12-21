import os
import asyncio
from typing import List, Optional, Set
from pathlib import Path
import shutil
import time
from pydantic import BaseModel
from contextlib import asynccontextmanager

from logging_utils import setup_logging
import logging

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from dotenv import load_dotenv
import google.generativeai as genai

# Reuse existing modules
from fetcher import (
    search_arxiv, search_semantic_scholar, search_core, search_pubmed, 
    unified_search, download_pdf, get_downloaded_papers, PaperInfo
)
from ingest import (
    get_weaviate_client,
    create_weaviate_schema,
    load_pdfs,
    create_vector_index,
    WEAVIATE_CLASS_NAME,
    configure_gemini
)

# Import agents
from agents import AgentRegistry, AgentContext
from agents.summarizer import summarizer_agent
from agents.methodology_extractor import methodology_extractor_agent
from agents.comparator import comparator_agent
from agents.gap_finder import gap_finder_agent
from agents.citation_analyzer import citation_analyzer_agent
from agents.general_qa import general_qa_agent

# Import memory system
from memory import (
    create_memory_collections, save_message, get_session_history,
    update_context, get_context, create_task, update_task_step
)

# Load environment variables
load_dotenv()
setup_logging("ScholarSync")
logger = logging.getLogger("ScholarSync.api")

# Configuration
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloaded_papers"))
# Ensure download dir exists
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_download_subdir(folder: str) -> Path:
    """
    Resolve a subfolder under DOWNLOAD_DIR and prevent path traversal.
    """
    base = DOWNLOAD_DIR.resolve()
    target = (DOWNLOAD_DIR / folder).resolve()
    if target == base:
        return target
    if base not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid folder")
    return target


# --- Pydantic Models ---

class SearchRequest(BaseModel):
    query: str
    max_results: int = 20
    tenant_id: Optional[str] = "default"
    author: Optional[str] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    sources: Optional[List[str]] = None  # ["arxiv", "semantic_scholar", "core", "pubmed"]

class PaperModel(BaseModel):
    title: str
    authors: List[str]
    published: str
    abstract: str
    pdf_url: str
    local_path: Optional[str] = None
    source: Optional[str] = None  # arxiv, semantic_scholar, core, pubmed
    
    # Helper to convert from fetcher.PaperInfo
    @classmethod
    def from_paper_info(cls, p):
        return cls(
            title=p.title,
            authors=p.authors,
            published=p.published,
            abstract=p.abstract,
            pdf_url=p.pdf_url,
            local_path=p.local_path,
            source=p.source
        )

class DownloadRequest(BaseModel):
    papers: List[PaperModel]
    folder: Optional[str] = None
    tenant_id: Optional[str] = "default"

class ChatRequest(BaseModel):
    message: str
    phase: str = "consultant" # "consultant" or "analyst"
    history: List[dict] = [] # List of {"role": "user"|"model", "parts": ["text"]}
    tenant_id: Optional[str] = "default"

class IngestRequest(BaseModel):
    filenames: Optional[List[str]] = None # If None, ingest all in download dir
    folder: Optional[str] = None
    tenant_id: Optional[str] = "default"

class ClearKBRequest(BaseModel):
    tenant_id: Optional[str] = "default"
    folder: Optional[str] = None

class DeletePaperRequest(BaseModel):
    filename: str

# --- System Prompts ---
CONSULTANT_PROMPT = """You are Thynk, an expert research consultant. Generate a compact search plan.

RESPONSE FORMAT (NO MARKDOWN):
Assistant
Goal: [One sentence describing what user wants to find]
Concepts: [Topic 1] • [Topic 2] • [Topic 3]
Methodologies: [Method 1] • [Method 2] • [Method 3]
Domains: [Domain 1] • [Domain 2] • [Domain 3]
Keywords: [Term 1] • [Term 2] • [Term 3] • [Term 4] • [Term 5]
Search Query: [clean search terms only]

RULES:
1. NO markdown formatting (no **, *, or backticks)
2. Use bullet separator ' • ' between items
3. Keep each section to ONE line
4. Search Query: simple keywords only, no special characters
5. Be concise - max 3-5 items per section
"""

ANALYST_PROMPT = """You are Thynk, a research analyst. Answer questions based on the provided paper context.

RESPONSE RULES:
1. Write in plain English. Avoid LaTeX notation - write equations in words or simplified form.
2. Use **bold** for key terms, concepts, and important words.
3. Use short paragraphs and bullet points for readability.
4. Put source citations at the end: [Paper Name, p.X]
5. If asked about system usage, say: "You can now ask questions about the papers."
6. If info isn't available, say so briefly.

FORMAT:
- Start with a 1-2 sentence **summary** answering the question
- Then provide key details in bullet points
- **Bold** important terms and findings
- Keep each bullet to 1-2 lines max

AVOID:
- Long paragraphs
- LaTeX symbols like \\( \\) or \\[ \\]
- Repeating the same information"""


# --- App Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting ScholarSync API...")
    configure_gemini()
    logger.info("ScholarSync API ready.")
    yield
    # Shutdown (if any)

app = FastAPI(title="ScholarSync API", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/search", response_model=List[PaperModel])
async def search_papers(req: SearchRequest):
    """Search papers across multiple sources with unified ranking."""
    t0 = time.perf_counter()
    loop = asyncio.get_event_loop()
    
    try:
        def _run_search():
            from fetcher import unified_search
            return unified_search(
                req.query,
                max_results=req.max_results,
                author=req.author,
                start_date=req.start_date,
                end_date=req.end_date,
                sources=req.sources  # None = all sources
            )
        
        sources_str = ", ".join(req.sources) if req.sources else "all"
        logger.info(
            "Unified search started | sources=%s max_results=%s author=%s dates=%s..%s",
            sources_str,
            req.max_results,
            (req.author or "").strip() or None,
            req.start_date,
            req.end_date,
        )
        papers = await asyncio.wait_for(
            loop.run_in_executor(None, _run_search),
            timeout=90.0  # 90 second timeout for multiple sources
        )
        logger.info("Search done | results=%d elapsed=%.2fs", len(papers), time.perf_counter() - t0)
        return [PaperModel.from_paper_info(p) for p in papers]
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Search timed out. Please try again with a simpler query.")
    except Exception as e:
        error_msg = str(e)
        if "rate limited" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(status_code=503, detail=f"Source rate limited: {error_msg}")
        if "UnexpectedEmptyPageError" in error_msg or "retry" in error_msg.lower():
            raise HTTPException(status_code=503, detail="Source temporarily unavailable. Please try again in a moment.")
        raise HTTPException(status_code=500, detail=f"Search failed: {error_msg}")

@app.post("/api/download")
async def download_papers(req: DownloadRequest):
    """Download list of papers."""
    results = []
    # Safety: default to tenant folder to avoid mixing sessions
    folder = req.folder or (req.tenant_id or "default")
    target_dir = DOWNLOAD_DIR / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Download started | papers=%d tenant=%s folder=%s", len(req.papers), req.tenant_id or "default", folder)
    
    # We need to reconvert Pydantic models back to PaperInfo-like objects for the downloader
    # Or just modify download logic. fetcher.download_pdf takes PaperInfo.
    # Let's simple create a dummy object or modify fetcher.PaperInfo to be pydantic-compatible?
    # Easier to just instantiate PaperInfo here.
    
    for p_model in req.papers:
        # Reconstruct PaperInfo matching fetcher.py's expectation
        p_info = PaperInfo(
            title=p_model.title,
            authors=p_model.authors,
            abstract=p_model.abstract,
            arxiv_id=p_model.pdf_url.split('/')[-1], # Basic extraction
            pdf_url=p_model.pdf_url,
            published=p_model.published,
            categories=[], # Not strictly needed for download
            local_path=p_model.local_path
        )
        
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(None, lambda: download_pdf(p_info, download_dir=target_dir))
        
        if path:
            p_model.local_path = path
            results.append(p_model)
            
    logger.info("Download done | downloaded=%d/%d folder=%s", len(results), len(req.papers), folder)
    return {"downloaded": len(results), "papers": results}

@app.post("/api/ingest")
async def ingest_papers_endpoint(req: IngestRequest):
    """Ingest downloaded papers into Weaviate."""
    try:
        t0 = time.perf_counter()
        filenames = req.filenames
        folder = req.folder or (req.tenant_id or "default")
        tenant_id = req.tenant_id or "default"
        target_files = []
        base_dir = DOWNLOAD_DIR / folder
        base_dir.mkdir(parents=True, exist_ok=True)
        if filenames:
            for fname in filenames:
                fpath = base_dir / fname
                if fpath.exists():
                    target_files.append(fpath)
        else:
            # All files in dir
             target_files = list(base_dir.glob("*.pdf"))
        
        if not target_files:
             return {"status": "no_files", "message": "No files found to ingest."}

        logger.info(
            "Ingest started | tenant=%s folder=%s files=%d",
            tenant_id,
            folder,
            len(target_files),
        )

        # Run ingestion logic
        # We'll reuse the logic from `ingest.py` but adapted for API context
        # Ideally `ingest.py` functions are reusable. 
        
        loop = asyncio.get_event_loop()
        
        # 1. Setup & Schema
        client = get_weaviate_client()
        create_weaviate_schema(client)
        
        # 2. Load PDFs
        documents = await loop.run_in_executor(
            None, 
            lambda: load_pdfs(specific_files=target_files)
        )
        
        # 3. Index
        if documents:
            result = await loop.run_in_executor(
                None, 
                lambda: create_vector_index(documents, client, tenant_id=tenant_id)
            )
        else:
            result = {"total_nodes": 0}
            
        client.close()
        logger.info(
            "Ingest done | tenant=%s total_nodes=%s elapsed=%.2fs",
            tenant_id,
            result.get("total_nodes", 0) if isinstance(result, dict) else 0,
            time.perf_counter() - t0,
        )
        return {"status": "success", "metrics": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear_kb")
async def clear_kb(req: ClearKBRequest):
    """Clear knowledge base for a specific tenant (and optional folder)."""
    tenant_id = req.tenant_id or "default"
    try:
        client = get_weaviate_client()
        if client.collections.exists(WEAVIATE_CLASS_NAME):
            collection = client.collections.get(WEAVIATE_CLASS_NAME)
            import weaviate.classes.query as wq
            # Delete all objects for this tenant
            collection.data.delete_many(
                where=wq.Filter.by_property("tenant_id").equal(tenant_id)
            )
        client.close()
        folder_deleted = False
        # Optionally clear folder (delete the entire directory). If folder isn't provided,
        # default to tenant_id for non-default tenants to maintain session isolation.
        folder = req.folder or (tenant_id if tenant_id != "default" else None)
        if folder:
            target_dir = _safe_download_subdir(folder)
            if target_dir.exists() and target_dir.is_dir():
                shutil.rmtree(target_dir, ignore_errors=True)
                folder_deleted = True
        return {"status": "cleared", "tenant_id": tenant_id, "folder_deleted": folder_deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/delete_paper")
async def delete_paper(req: DeletePaperRequest):
    """Delete all chunks for a specific paper from Weaviate and optionally the PDF file."""
    try:
        client = get_weaviate_client()
        deleted_count = 0
        
        if client.collections.exists(WEAVIATE_CLASS_NAME):
            collection = client.collections.get(WEAVIATE_CLASS_NAME)
            import weaviate.classes.query as wq
            
            # Delete all chunks with this filename
            result = collection.data.delete_many(
                where=wq.Filter.by_property("filename").equal(req.filename)
            )
            deleted_count = result.successful if hasattr(result, 'successful') else 0
        
        client.close()
        
        # Also try to delete the PDF file
        pdf_deleted = False
        for pdf_path in DOWNLOAD_DIR.glob(f"**/{req.filename}"):
            try:
                pdf_path.unlink()
                pdf_deleted = True
            except:
                pass
        
        return {
            "status": "deleted",
            "filename": req.filename,
            "chunks_deleted": deleted_count,
            "pdf_deleted": pdf_deleted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Unified chat endpoint.
    If phase == 'consultant': Uses simple Gemini chat.
    If phase == 'analyst': Uses RAG against Weaviate + Gemini.
    """
    configure_gemini()
    
    if req.phase == "consultant":
        # -- Consultant Logic --
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=CONSULTANT_PROMPT
        )
        
        # Reconstruct chat history for Gemini
        formatted_history = []
        for h in req.history:
            formatted_history.append({
                "role": h["role"],
                "parts": h["parts"]
            })
            
        chat_session = model.start_chat(history=formatted_history)
        response = chat_session.send_message(req.message)

        # Try to extract a search query if present (with or without backticks)
        import re
        search_query = None
        # First try with backticks
        pattern_backticks = r"Search Query:\s*`([^`]+)`"
        match = re.search(pattern_backticks, response.text)
        if match:
            search_query = match.group(1).strip()
        else:
            # Try without backticks - get the rest of the line after "Search Query:"
            pattern_plain = r"Search Query:\s*(.+?)(?:\n|$)"
            match = re.search(pattern_plain, response.text)
            if match:
                search_query = match.group(1).strip()
        
        # Save to session memory
        save_message(req.tenant_id, "user", req.message)
        save_message(req.tenant_id, "assistant", response.text, agent="ConsultantAgent")
        
        # Update context
        update_context(req.tenant_id, agent_used="ConsultantAgent", query=req.message)
        
        return {
            "response": response.text,
            "search_query": search_query,
            "agent": "ConsultantAgent"  # Add agent field for badge
        }

    elif req.phase == "analyst":
        # -- Analyst Logic (RAG) --
        # We need to perform retrieval + generation
        
        # 1. Connect to Weaviate
        client = get_weaviate_client()
        if not client.collections.exists(WEAVIATE_CLASS_NAME):
            client.close()
            return {"response": "Knowledge base not ready. Please ingest papers first."}
        
        collection = client.collections.get(WEAVIATE_CLASS_NAME)
        import weaviate.classes.query as wq
        
        # 2. Retrieve - get more chunks and prefer larger ones with more context
        loop = asyncio.get_event_loop()
        
        # First try to get larger chunks (node_level 0 or 1) for better context
        tenant_filter = wq.Filter.by_property("tenant_id").equal(req.tenant_id or "default")
        
        results = await loop.run_in_executor(
            None,
            lambda: collection.query.near_text(
                query=req.message,
                limit=15,  # Get more chunks for better coverage
                return_metadata=wq.MetadataQuery(distance=True),
                filters=tenant_filter
            )
        )
        
        if not results.objects:
            client.close()
            return {"response": "No relevant info found in papers. Try asking a different question."}
            
        # 3. Context Merging - prioritize medium chunks (best balance)
        context_parts = []
        sources = set()
        chunk_stats = {"retrieved": len(results.objects), "used": 0, "skipped_short": 0, "skipped_equations": 0}
        
        # Sort: prefer medium chunks (level 1), then by text length
        sorted_objects = sorted(
            results.objects,
            key=lambda x: (
                abs(x.properties.get("node_level", 2) - 1),  # Prefer level 1 (medium)
                -len(x.properties.get("text", ""))
            )
        )
        
        for obj in sorted_objects:
            text = obj.properties.get("text", "").strip()
            node_level = obj.properties.get("node_level", 2)
            
            # Skip very short chunks
            if len(text) < 100:
                chunk_stats["skipped_short"] += 1
                continue
                
            # Skip chunks that are mostly numbers/symbols (likely equations)
            alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
            if alpha_ratio < 0.5:
                chunk_stats["skipped_equations"] += 1
                continue
                
            fname = obj.properties.get("filename", "unknown")
            page = obj.properties.get("page_number", 0)
            context_parts.append(f"(Source: {fname}, Page {page})\n{text}")
            sources.add(fname)
            chunk_stats["used"] += 1
            
            # Use 8 quality chunks max
            if len(context_parts) >= 8:
                break
        
        # Debug-only stats (kept out of normal console output)
        logger.debug("Chunk stats: %s", chunk_stats)
            
        context_str = "\n\n---\n\n".join(context_parts)
        
        if not context_parts:
            client.close()
            return {"response": f"Found {chunk_stats['retrieved']} chunks but none had useful text content. The paper may be mostly equations/figures."}
        client.close()
        
        # 4. Check if a specialized agent should handle this query
        matching_agent = AgentRegistry.find_matching(req.message)
        
        if matching_agent:
            # Route to specialized agent
            logger.info("Routing to agent: %s", matching_agent.name)
            agent_context = AgentContext(
                tenant_id=req.tenant_id or "default",
                papers=list(sources),
                chat_history=req.history,
                metadata={
                    "paper_context": context_str,
                    "sources": list(sources)
                }
            )
            agent_response = await matching_agent.run(req.message, agent_context)
            
            # Save to session memory
            save_message(req.tenant_id, "user", req.message)
            save_message(req.tenant_id, "assistant", agent_response.content, agent=matching_agent.name)
            
            # Update context
            update_context(req.tenant_id, agent_used=matching_agent.name, query=req.message)
            
            return {
                "response": agent_response.content,
                "sources": agent_response.sources,
                "agent": matching_agent.name
            }
        
        # 5. Default: Use standard RAG response
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=ANALYST_PROMPT
        )
        
        prompt = f"Context:\n{context_str}\n\nQuestion: {req.message}"
        response = model.generate_content(prompt)
        
        # Save to session memory
        save_message(req.tenant_id, "user", req.message)
        save_message(req.tenant_id, "assistant", response.text, agent="GeneralQA")
        
        # Update context
        update_context(req.tenant_id, agent_used="GeneralQA", query=req.message)
        
        return {
            "response": response.text,
            "sources": list(sources)
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid phase")


@app.get("/api/status")
async def get_status(tenant_id: Optional[str] = Query(default=None)):
    """System status (Weaviate, Paper Count). If tenant_id is provided, scope stats to that tenant."""
    try:
        # Paper list: global (all folders) or tenant-scoped folder
        if tenant_id:
            base = DOWNLOAD_DIR / tenant_id
            papers = list(base.glob("*.pdf")) if base.exists() else []
        else:
            papers = get_downloaded_papers()

        client = get_weaviate_client()
        
        chunk_count = 0
        chunk_count_all = 0
        weaviate_connected = False
        
        if client.collections.exists(WEAVIATE_CLASS_NAME):
            import weaviate.classes.aggregate as wag
            import weaviate.classes.query as wq
            collection = client.collections.get(WEAVIATE_CLASS_NAME)
            # Global aggregation
            agg_all = collection.aggregate.over_all(total_count=True)
            chunk_count_all = agg_all.total_count

            # Tenant-scoped aggregation (if requested)
            if tenant_id:
                try:
                    agg_tenant = collection.aggregate.over_all(
                        total_count=True,
                        filters=wq.Filter.by_property("tenant_id").equal(tenant_id),
                    )
                    chunk_count = agg_tenant.total_count
                except Exception:
                    # Fallback: if filtering isn't supported by the client version, return global count
                    chunk_count = chunk_count_all
            else:
                chunk_count = chunk_count_all

            weaviate_connected = True
            
        client.close()
        
        return {
            "weaviate_connected": weaviate_connected,
            "tenant_id": tenant_id,
            "indexed_chunks": chunk_count,
            "indexed_chunks_all": chunk_count_all,
            "downloaded_papers": len(papers),
            "paper_list": [p.name for p in papers]
        }
    except Exception as e:
        return {
            "weaviate_connected": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("UVICORN_LOG_LEVEL", "info"),
        access_log=os.getenv("UVICORN_ACCESS_LOG", "0") == "1",
    )
