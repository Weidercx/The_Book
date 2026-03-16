# The_Book/agents/factory.py
# Agent factory for spawning and coordinating SDLC role pools

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AgentFactory:
    """
    Factory for spawning and managing agent pools for different SDLC roles.
    
    Coordinates ingest agents, QA agents, schema agents, dedup agents, etc.
    Provides high-level orchestration for multi-stage pipelines.
    """
    
    def __init__(self, config: Dict[str, Any], logger_instance: logging.Logger = None):
        """
        Initialize factory.
        
        Args:
            config: Global config dict (from config/*.yaml or env)
            logger_instance: Optional logger instance
        """
        self.config = config
        self.logger = logger_instance or logger
        self.agents = {}
        self.results_cache = {}
    
    def register_agent_class(self, role: str, agent_class: type):
        """
        Register an agent class for a given role.
        
        Args:
            role: Role name (e.g., "ingest", "qa", "schema", "dedup", "license")
            agent_class: Agent class (must inherit from BaseAgent)
        """
        self.agents[role] = agent_class
        self.logger.info(f"Registered agent class for role '{role}'")
    
    async def spawn_agents(self, role: str, count: int, configs: List[Dict[str, Any]]) -> List[BaseAgent]:
        """
        Spawn multiple agents of the same role.
        
        Args:
            role: Agent role (must be registered)
            count: Number of agents to spawn (usually = number of configs)
            configs: List of config dicts for each agent
        
        Returns:
            List of spawned agent instances
        """
        if role not in self.agents:
            raise ValueError(f"Agent role '{role}' not registered")
        
        agent_class = self.agents[role]
        spawned = []
        
        for i, agent_config in enumerate(configs[:count]):
            agent_name = f"{role}-{i}"
            agent = agent_class(agent_name, agent_config)
            spawned.append(agent)
            self.logger.info(f"Spawned agent: {agent_name}")
        
        return spawned
    
    async def run_agents_parallel(self, agents: List[BaseAgent], **kwargs) -> List[Dict[str, Any]]:
        """
        Run a list of agents in parallel and collect results.
        
        Args:
            agents: List of agent instances
            **kwargs: Arguments to pass to each agent's run() method
        
        Returns:
            List of result dicts from each agent
        """
        self.logger.info(f"Running {len(agents)} agents in parallel")
        tasks = [agent.run(**kwargs) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        clean_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Agent {i} failed: {result}")
                clean_results.append({
                    "status": "error",
                    "message": str(result),
                    "agent_index": i
                })
            else:
                clean_results.append(result)
        
        return clean_results
    
    async def ingest_all_archives(self, archive_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Full ingest phase: spawn IngestAgent per enabled archive and run in parallel.
        
        Args:
            archive_configs: List of archive configs from sources.yaml
        
        Returns:
            Aggregated ingest results
        """
        enabled_archives = [cfg for cfg in archive_configs if cfg.get("v1_enabled", False)]
        self.logger.info(f"Starting ingest for {len(enabled_archives)} enabled archives")
        
        ingest_agents = await self.spawn_agents("ingest", len(enabled_archives), enabled_archives)
        results = await self.run_agents_parallel(ingest_agents)
        
        self.results_cache["ingest_results"] = results
        return results
    
    async def validate_and_normalize(self, ingest_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validation & normalization phase: run SchemaAgent + QAAgent on batch.
        
        Args:
            ingest_results: Results from ingest phase
        
        Returns:
            Normalized and validated witness records
        """
        self.logger.info("Starting validation and normalization phase")
        
        # Spawn one SchemaAgent + one QAAgent for batch processing
        schema_config = {"input_data": ingest_results}
        qa_config = {"input_data": ingest_results}
        
        schema_agents = await self.spawn_agents("schema", 1, [schema_config])
        qa_agents = await self.spawn_agents("qa", 1, [qa_config])
        
        schema_results = await self.run_agents_parallel(schema_agents)
        qa_results = await self.run_agents_parallel(qa_agents)
        
        self.results_cache["schema_results"] = schema_results
        self.results_cache["qa_results"] = qa_results
        
        return {
            "schema": schema_results[0] if schema_results else {},
            "qa": qa_results[0] if qa_results else {}
        }
    
    async def orchestrate_full_pipeline(self, archive_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Full end-to-end pipeline: ingest → normalize → QA → dedup → license gate → export.
        
        Args:
            archive_configs: List of all archive configs
        
        Returns:
            Final aggregated pipeline results
        """
        self.logger.info("=== STARTING FULL INGEST PIPELINE ===")
        pipeline_start = datetime.utcnow()
        
        # Phase 1: Ingest
        self.logger.info("Phase 1: Ingest")
        ingest_results = await self.ingest_all_archives(archive_configs)
        
        # Phase 2: Normalize + Validate
        self.logger.info("Phase 2: Normalize + Validate")
        norm_val_results = await self.validate_and_normalize(ingest_results)
        
        # Phase 3-6: Dedup, License, Reporting, Export (stubs for now)
        self.logger.info("Phase 3-6: Dedup, License, Reporting, Export (not yet implemented)")
        
        pipeline_end = datetime.utcnow()
        
        return {
            "status": "in_progress",
            "pipeline_start": pipeline_start.isoformat(),
            "pipeline_end": pipeline_end.isoformat(),
            "duration_seconds": (pipeline_end - pipeline_start).total_seconds(),
            "phases": {
                "ingest": ingest_results,
                "normalize_validate": norm_val_results,
            },
            "cache": self.results_cache
        }
