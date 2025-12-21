# ScholarSync: Design Notes and Technical Decisions

## System Overview

ScholarSync is a multi-agent research assistant designed to help researchers discover, download, and analyze academic papers from ArXiv. The system uses specialized AI agents to provide expert-level responses to different types of research questions.

---

## Architecture Decisions

### 1. Multi-Agent Design

**Decision**: Implement a specialized agent system with 6 distinct agents instead of a single general-purpose agent.

**Rationale**:
- Different research questions require different analysis approaches
- Specialized prompts yield better results than generic ones
- Allows for task-specific optimizations (e.g., structured summaries vs. gap analysis)
- Improves user experience by providing expert-level responses

**Implementation**:
- Agent Registry manages all agents and their metadata
- Keyword-based routing selects the appropriate agent
- Each agent has a specialized system prompt
- Fallback to GeneralQAAgent for unmatched queries

### 2. Hierarchical Chunking Strategy

**Decision**: Use three levels of chunk sizes (large, medium, small) instead of a single chunk size.

**Rationale**:
- Large chunks (2048 tokens) provide broad context
- Medium chunks (512 tokens) balance context and precision
- Small chunks (128 tokens) enable precise matching
- Retrieval can adaptively select the best chunk size for each query

**Implementation**:
- RecursiveCharacterTextSplitter from LangChain
- Separate chunking passes for each level
- Metadata tags for chunk level identification
- Preference for medium chunks during retrieval

### 3. Two-Phase Workflow

**Decision**: Split the user experience into "Consultant" and "Analyst" phases.

**Rationale**:
- Consultant phase helps users with vague ideas (common starting point)
- Provides structured search plans rather than raw queries
- Analyst phase focuses on deep analysis after papers are indexed
- Clear separation of concerns improves UX

**Implementation**:
- Phase selection in API (consultant/analyst parameter)
- Different system prompts for each phase
- Consultant uses simple Gemini chat
- Analyst uses RAG + specialized agents

### 4. Keyword-Based Agent Routing

**Decision**: Use keyword matching for agent selection instead of LLM-based routing.

**Rationale**:
- Faster response times (no additional LLM call)
- Deterministic and predictable behavior
- Lower API costs
- Sufficient accuracy for the use case (>85% in testing)

**Implementation**:
- Each agent registers trigger keywords
- Priority scoring (keywords at query start weighted higher)
- Best match wins, fallback to GeneralQAAgent

### 5. Cloud-Native Vector Storage

**Decision**: Use Weaviate Cloud instead of local vector database.

**Rationale**:
- No infrastructure management required
- Free tier (1GB) sufficient for most research projects
- Built-in multi-tenancy support
- Scalable without code changes

**Implementation**:
- Weaviate client with Gemini embeddings
- Tenant ID for session isolation
- Metadata filtering for precise retrieval

---

## Component Details

### Frontend (React + Vite)

**Technology Choice**: React with Vite instead of Chainlit or Streamlit

**Rationale**:
- Full control over UI/UX
- Better integration with custom components
- Professional, production-ready interface
- Separation of concerns (frontend/backend)

**Key Components**:
- `ChatPanel`: Main interface with markdown rendering
- `StatusPanel`: System status and paper count
- `api.js`: Axios-based API client

### Backend (FastAPI)

**Technology Choice**: FastAPI instead of Flask or Django

**Rationale**:
- Async support (better for AI/LLM calls)
- Automatic API documentation (OpenAPI/Swagger)
- Type safety with Pydantic models
- High performance

**Key Endpoints**:
- `/api/chat`: Unified chat (consultant + analyst)
- `/api/search`: ArXiv paper search
- `/api/download`: PDF download
- `/api/ingest`: Embedding and indexing
- `/api/status`: System health

### LLM Strategy

**Consultant**: Gemini 2.5 Flash
- Fast response times
- Structured output generation
- Cost-effective for ideation

**Analyst**: Gemini 2.5 Flash with RAG
- Same model for consistency
- RAG provides context from papers
- Specialized agent prompts improve quality

**Embeddings**: Gemini text-embedding-004
- Free with Gemini API
- High quality for academic text
- Native integration with Weaviate

---

## Data Flow

### Paper Discovery Flow
```
User Idea → Consultant Agent → Search Query → ArXiv API → Results → 
User Selection → PDF Download → Local Storage
```

### Ingestion Flow
```
PDF Files → Text Extraction → Hierarchical Chunking → 
Embeddings (Gemini) → Weaviate Index → Ready for Q&A
```

### Query Flow
```
User Question → Query Embedding → Vector Search (Weaviate) → 
Retrieve Chunks → Agent Routing → Specialized Response → 
Cited Answer
```

---

## Key Optimizations

### 1. Chunk Quality Filtering
- Skip chunks < 100 characters (too short)
- Skip chunks with < 50% alphabetic characters (likely equations/tables)
- Prefer medium-sized chunks for better context

### 2. Retrieval Strategy
- Retrieve 15 chunks initially
- Sort by chunk level (prefer medium)
- Use top 8 quality chunks for context
- Include source metadata for citations

### 3. Multi-Tenancy
- Each session has isolated tenant_id
- Papers stored in separate folders
- Weaviate filters by tenant_id
- Clean separation prevents cross-contamination

---

## Trade-offs and Limitations

### Trade-offs

1. **Keyword Routing vs. LLM Routing**
   - Chose keyword for speed/cost
   - Sacrifices some accuracy for better UX

2. **Cloud Vector DB vs. Local**
   - Chose cloud for simplicity
   - Requires internet connection
   - Free tier has storage limits

3. **Three Chunk Levels vs. More**
   - Chose three as a balance
   - More levels = more storage, marginal gains

### Known Limitations

1. **ArXiv API Rate Limits**
   - Max 20 papers per search (API limitation)
   - Timeout after 60 seconds
   - No bulk downloads

2. **PDF Parsing Challenges**
   - Equations may not parse well
   - Tables and figures lose formatting
   - Optional LlamaParse for better results

3. **Context Window**
   - Limited to 8 chunks per query
   - Very large papers may not fit entirely
   - Trade-off between breadth and depth

---

## Future Improvements

1. **LLM-Based Routing**: Use a fast LLM to improve agent selection accuracy
2. **Hybrid Search**: Combine semantic search with keyword search
3. **Paper Recommendations**: Suggest related papers based on user's collection
4. **Multi-Source Support**: Add support for more databases (IEEE, ACM, etc.)
5. **Persistent Sessions**: Save user sessions across browser refreshes
6. **Export Features**: Export summaries and analysis as PDF/Markdown

---

## Security Considerations

1. **Path Traversal Prevention**: `_safe_download_subdir()` validates folder paths
2. **API Key Protection**: Environment variables for sensitive data
3. **CORS Configuration**: Restricted in production deployment
4. **Input Validation**: Pydantic models validate all API inputs
5. **Rate Limiting**: Consider implementing for production use

---

## Performance Metrics

*Based on typical usage patterns:*

- **Consultant Response Time**: 2-4 seconds
- **Paper Search**: 5-15 seconds (ArXiv API dependent)
- **PDF Download**: 2-5 seconds per paper
- **Ingestion**: 30-60 seconds per paper (depends on size)
- **Analyst Query**: 3-6 seconds (RAG + generation)
- **Agent Routing Accuracy**: 85-90% (keyword-based)

---

## Development Principles

1. **User-First Design**: Prioritize user experience over technical complexity
2. **Modularity**: Each component is independently testable and replaceable
3. **Fail Gracefully**: Provide meaningful error messages
4. **Logging**: Comprehensive logging for debugging and monitoring
5. **Documentation**: Inline comments and external docs for maintainability
