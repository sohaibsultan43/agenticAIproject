"""
ScholarSync - General Q&A Agent (OpenAI GPT-5 mini)
====================================================
General RAG agent for answering questions about papers.
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

GENERAL_QA_PROMPT = """You are a research paper Q&A assistant. Answer questions about research papers accurately and comprehensively.

GUIDELINES:
- Provide clear, accurate answers based ONLY on the paper content
- Quote specific findings when relevant
- If information is not in the papers, say so
- Be precise and cite sources when possible
- For complex questions, break down your answer into clear points
- Use bullet points and formatting for readability

Answer the user's question based on the paper content provided."""


class GeneralQAAgent(BaseAgent):
    """General Q&A agent for paper questions."""
    
    name = "GeneralQAAgent"
    description = "Answers general questions about research papers using RAG"
    agent_type = AgentType.GENERAL_QA
    
    # No keywords - this is the fallback agent
    trigger_keywords = []
    
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
        """Answer general questions about papers."""
        self.logger.info("General Q&A agent executing | tenant=%s", context.tenant_id)
        
        if not self.client:
            return AgentResponse(
                content="Error: OpenAI API key not configured.",
                agent_type=self.agent_type,
                success=False,
                error="OPENAI_API_KEY not set"
            )
        
        paper_context = context.metadata.get("paper_context", "")
        sources = context.metadata.get("sources", [])
        
        if not paper_context:
            return AgentResponse(
                content="No paper content available. Please ingest papers first.",
                agent_type=self.agent_type,
                success=False,
                error="No paper context"
            )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": GENERAL_QA_PROMPT},
                    {"role": "user", "content": f"""Answer the following question based on the paper content.

Paper Content:
{paper_context}

Question: {query}"""}
                ]
            )
            
            content = response.choices[0].message.content
            
            self.logger.info("General Q&A completed | sources=%d", len(sources))
            
            return AgentResponse(
                content=content,
                agent_type=self.agent_type,
                sources=sources,
                metadata={"query": query},
                success=True
            )
            
        except Exception as e:
            self.logger.error("General Q&A failed: %s", str(e))
            return AgentResponse(
                content=f"Error answering question: {str(e)}",
                agent_type=self.agent_type,
                success=False,
                error=str(e)
            )


# Create singleton and register
general_qa_agent = GeneralQAAgent()
AgentRegistry.register(general_qa_agent)
