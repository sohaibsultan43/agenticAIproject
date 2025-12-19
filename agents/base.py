"""
ScholarSync - Agent Base Classes
================================
Base infrastructure for all specialized agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger("ScholarSync.agents")


class AgentType(Enum):
    """Types of available agents."""
    SUMMARIZER = "summarizer"
    METHODOLOGY_EXTRACTOR = "methodology_extractor"
    COMPARATOR = "comparator"
    GAP_FINDER = "gap_finder"
    CITATION_ANALYZER = "citation_analyzer"
    TREND_ANALYZER = "trend_analyzer"
    WRITING_ASSISTANT = "writing_assistant"
    GENERAL_QA = "general_qa"  # General RAG Q&A


@dataclass
class AgentContext:
    """Context passed to agents for execution."""
    tenant_id: str = "default"
    papers: List[str] = field(default_factory=list)  # List of paper filenames in KB
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Standardized response from agents."""
    content: str  # Main response content (markdown formatted)
    agent_type: AgentType  # Which agent generated this
    sources: List[str] = field(default_factory=list)  # Papers used
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional data
    success: bool = True
    error: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all ScholarSync agents."""
    
    name: str = "BaseAgent"
    description: str = "Base agent class"
    agent_type: AgentType = None
    
    # Keywords that trigger this agent
    trigger_keywords: List[str] = []
    
    def __init__(self):
        self.logger = logging.getLogger(f"ScholarSync.agents.{self.name}")
    
    @abstractmethod
    async def run(self, query: str, context: AgentContext) -> AgentResponse:
        """
        Execute the agent's task.
        
        Args:
            query: User's query/request
            context: Execution context with tenant, papers, history
            
        Returns:
            AgentResponse with results
        """
        pass
    
    def get_match_score(self, query: str) -> int:
        """
        Get a score for how well this agent matches the query.
        Higher score = better match.
        
        Args:
            query: User's query
            
        Returns:
            Match score (0 = no match)
        """
        query_lower = query.lower()
        score = 0
        
        for keyword in self.trigger_keywords:
            if keyword in query_lower:
                # Find position of keyword
                pos = query_lower.find(keyword)
                
                # Much higher score for keywords at the very start (intent words)
                if pos < 15:
                    score += 20
                elif pos < 40:
                    score += 10
                else:
                    # Lower score for keywords later in query (might be in paper titles)
                    score += 2
        
        return score
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities for discovery."""
        return {
            "name": self.name,
            "type": self.agent_type.value if self.agent_type else None,
            "description": self.description,
            "triggers": self.trigger_keywords
        }


class AgentRegistry:
    """Registry for discovering and routing to agents."""
    
    _agents: Dict[AgentType, BaseAgent] = {}
    
    @classmethod
    def register(cls, agent: BaseAgent):
        """Register an agent."""
        if agent.agent_type:
            cls._agents[agent.agent_type] = agent
            logger.info("Registered agent: %s", agent.name)
    
    @classmethod
    def get(cls, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get agent by type."""
        return cls._agents.get(agent_type)
    
    @classmethod
    def find_matching(cls, query: str) -> Optional[BaseAgent]:
        """Find agent that best matches the query using scoring."""
        best_agent = None
        best_score = 0
        
        for agent in cls._agents.values():
            # Skip the general QA agent in routing
            if agent.agent_type == AgentType.GENERAL_QA:
                continue
                
            score = agent.get_match_score(query)
            if score > best_score:
                best_score = score
                best_agent = agent
        
        # Log the routing decision
        if best_agent:
            logger.info("Agent routing: '%s' -> %s (score: %d)", 
                       query[:50], best_agent.name, best_score)
        
        # If no specialized agent matches, use General Q&A
        if not best_agent or best_score == 0:
            best_agent = cls._agents.get(AgentType.GENERAL_QA)
            if best_agent:
                logger.info("Agent routing: '%s' -> %s (default)", 
                           query[:50], best_agent.name)
        
        return best_agent
    
    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [agent.get_capabilities() for agent in cls._agents.values()]
