"""
ScholarSync - Summarizer Agent (OpenAI GPT-5 mini)
===================================================
Agent specialized in generating structured summaries of research papers.
"""

import os
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

from .base import (
    BaseAgent,
    AgentContext,
    AgentResponse,
    AgentType,
    AgentRegistry
)

load_dotenv()

# Summarizer-specific system prompt
SUMMARIZER_PROMPT = """You are a research paper summarization expert. Generate comprehensive, well-structured summaries of academic papers.

OUTPUT FORMAT (use this exact structure):

## Summary: [Paper Title]

**TL;DR:** [One sentence summary - max 30 words]

### Key Findings
• [Finding 1]
• [Finding 2]
• [Finding 3]

### Methodology
• **Approach:** [Main approach/technique used]
• **Data:** [Dataset or data sources]
• **Evaluation:** [How results were evaluated]

### Main Contributions
1. [Contribution 1]
2. [Contribution 2]

### Limitations & Future Work
• [Limitation or future direction]

---
*Source: [filename]*

RULES:
- Use bullet points for readability
- Bold important terms with **term**
- Keep each bullet to 1-2 lines max
- Be specific, not generic
- If information is missing, skip that section
- Never invent information not in the source"""


class SummarizerAgent(BaseAgent):
    """Agent for generating structured paper summaries."""
    
    name = "SummarizerAgent"
    description = "Generates structured summaries of research papers with key findings, methodology, and contributions"
    agent_type = AgentType.SUMMARIZER
    
    # Keywords that trigger this agent
    trigger_keywords = [
        "summarize",
        "summary",
        "summarise",
        "tldr",
        "tl;dr",
        "overview",
        "brief",
        "key points",
        "main points",
        "what is this paper about",
        "explain this paper"
    ]
    
    def __init__(self):
        super().__init__()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
    
    async def run(self, query: str, context: AgentContext) -> AgentResponse:
        """
        Generate a structured summary of papers.
        
        Args:
            query: User's query (e.g., "summarize this paper")
            context: Context with tenant_id and metadata
            
        Returns:
            AgentResponse with structured summary
        """
        self.logger.info("Summarizer agent executing | tenant=%s", context.tenant_id)
        
        if not self.client:
            return AgentResponse(
                content="Error: OpenAI API key not configured.",
                agent_type=self.agent_type,
                success=False,
                error="OPENAI_API_KEY not set"
            )
        
        # Get paper content from context
        paper_context = context.metadata.get("paper_context", "")
        sources = context.metadata.get("sources", [])
        
        if not paper_context:
            return AgentResponse(
                content="No paper content available to summarize. Please ingest papers first.",
                agent_type=self.agent_type,
                success=False,
                error="No paper context"
            )
        
        try:
            # Generate summary using GPT-5 mini
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": SUMMARIZER_PROMPT},
                    {"role": "user", "content": f"""Based on the following paper content, generate a structured summary.

Paper Content:
{paper_context}

User Query: {query}

Generate a comprehensive summary following the output format."""}
                ]
            )
            
            content = response.choices[0].message.content
            
            self.logger.info("Summarizer agent completed | sources=%d", len(sources))
            
            return AgentResponse(
                content=content,
                agent_type=self.agent_type,
                sources=sources,
                metadata={"query": query},
                success=True
            )
            
        except Exception as e:
            self.logger.error("Summarizer agent failed: %s", str(e))
            return AgentResponse(
                content=f"Error generating summary: {str(e)}",
                agent_type=self.agent_type,
                success=False,
                error=str(e)
            )


# Create singleton instance and register
summarizer_agent = SummarizerAgent()
AgentRegistry.register(summarizer_agent)
