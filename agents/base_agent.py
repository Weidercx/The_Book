# The_Book/agents/base_agent.py
# Abstract base class for SDLC agents

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base for stateless, async-capable SDLC agents.
    
    Each agent (IngestAgent, QAAgent, SchemaAgent, etc.) handles one discrete role
    and returns structured results. Agents are designed to run in parallel pools.
    """
    
    def __init__(self, agent_name: str, config: Dict[str, Any] = None):
        """
        Initialize agent.
        
        Args:
            agent_name: Human-readable name (e.g., "IngestAgent-oshb")
            config: Optional configuration dict
        """
        self.agent_name = agent_name
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self.start_time = None
        self.end_time = None
    
    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute agent task. Must be implemented per-agent.
        
        Returns:
            Structured result dict with status, results, and metadata
        """
        pass
    
    def _make_result(
        self,
        status: str,  # "success", "warning", "error"
        message: str,
        data: Any = None,
        **metadata
    ) -> Dict[str, Any]:
        """
        Construct standardized result envelope for all agent outputs.
        """
        return {
            "agent_name": self.agent_name,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else None,
            "data": data,
            **metadata
        }
