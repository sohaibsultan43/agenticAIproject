"""
ScholarSync - Methodology Extractor Agent (OpenAI GPT-5 mini)
==============================================================
Agent specialized in extracting research methodologies from papers.
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

METHODOLOGY_PROMPT = """You are a research methodology extraction expert. Extract and structure the methodology from academic papers.

OUTPUT FORMAT (use this exact structure):

## Methodology: [Paper Title]

### Research Approach
• **Type:** [Experimental/Theoretical/Survey/Case Study/etc.]
• **Design:** [Brief description of overall research design]

### Data & Materials
• **Dataset:** [Name and size of dataset, or "N/A"]
• **Data Source:** [Where data came from]
• **Sample Size:** [If applicable]

### Methods & Techniques
• **Primary Method:** [Main technique/algorithm used]
• **Tools/Frameworks:** [Software, libraries, frameworks]
• **Implementation:** [Key implementation details]

### Evaluation
• **Metrics:** [Performance metrics used]
• **Baselines:** [What they compared against]
• **Validation:** [How results were validated]

### Experimental Setup
• **Hardware:** [If mentioned]
• **Parameters:** [Key hyperparameters or settings]

---
*Source: [filename]*

RULES:
- Extract ONLY what's explicitly stated in the paper
- Use bullet points for clarity
- Bold key terms with **term**
- If a section is not applicable or not found, write "Not specified in source"
- Be precise and technical"""


class MethodologyExtractorAgent(BaseAgent):
    """Agent for extracting research methodologies."""
    
    name = "MethodologyExtractorAgent"
    description = "Extracts research methods, datasets, algorithms, and experimental setup from papers"
    agent_type = AgentType.METHODOLOGY_EXTRACTOR
    
    trigger_keywords = [
        "methodology",
        "method",
        "methods",
        "approach",
        "technique",
        "algorithm",
        "dataset",
        "experimental setup",
        "how did they",
        "what method",
        "what approach"
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
        """Extract methodology from papers."""
        self.logger.info("Methodology extractor executing | tenant=%s", context.tenant_id)
        
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
                    {"role": "system", "content": METHODOLOGY_PROMPT},
                    {"role": "user", "content": f"""Based on the following paper content, extract the methodology.

Paper Content:
{paper_context}

User Query: {query}

Extract the methodology following the output format."""}
                ]
            )
            
            content = response.choices[0].message.content
            
            self.logger.info("Methodology extraction completed | sources=%d", len(sources))
            
            return AgentResponse(
                content=content,
                agent_type=self.agent_type,
                sources=sources,
                metadata={"query": query},
                success=True
            )
            
        except Exception as e:
            self.logger.error("Methodology extraction failed: %s", str(e))
            return AgentResponse(
                content=f"Error extracting methodology: {str(e)}",
                agent_type=self.agent_type,
                success=False,
                error=str(e)
            )


# Create singleton and register
methodology_extractor_agent = MethodologyExtractorAgent()
AgentRegistry.register(methodology_extractor_agent)
