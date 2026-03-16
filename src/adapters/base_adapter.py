# The_Book/src/adapters/base_adapter.py
# Abstract base class for all archive adapters

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..core import WitnessRecord, ArchiveConfig

logger = logging.getLogger(__name__)

class BaseAdapter(ABC):
    """
    Abstract base class for archive-specific ingest adapters.
    
    Each archive (OSHB, SBLGNT, ORACC, CDLI, etc.) implements this interface
    to fetch and normalize its source materials into unified WitnessRecord format.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with archive configuration.
        
        Args:
            config: Archive config dict from sources.yaml (name, url, api_endpoint, etc.)
        """
        self.config = config
        self.archive_name = config.get("name", "Unknown")
        self.url = config.get("url")
        self.api_endpoint = config.get("api_endpoint")
        self.license_code = config.get("license")
        self.logger = logging.getLogger(f"adapter.{self.archive_name}")
    
    @abstractmethod
    async def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch raw records from archive.
        
        Returns list of dictionaries with raw fields from source.
        Must be implemented per-archive.
        """
        pass
    
    @abstractmethod
    def parse(self, raw_records: List[Dict[str, Any]]) -> List[WitnessRecord]:
        """
        Parse raw archive records into unified WitnessRecord format.
        
        Args:
            raw_records: List of dicts from fetch()
        
        Returns:
            List of normalized WitnessRecord objects
        
        Must be implemented per-archive.
        """
        pass
    
    async def run(self, **kwargs) -> List[WitnessRecord]:
        """
        Full ingest pipeline: fetch + parse.
        
        Returns normalized witness records ready for validation.
        """
        try:
            self.logger.info(f"Starting ingest from {self.archive_name}")
            raw_records = await self.fetch(**kwargs)
            self.logger.info(f"Fetched {len(raw_records)} raw records from {self.archive_name}")
            
            witness_records = self.parse(raw_records)
            self.logger.info(f"Parsed {len(witness_records)} witness records from {self.archive_name}")
            
            return witness_records
        except Exception as e:
            self.logger.error(f"Adapter error in {self.archive_name}: {e}")
            raise
    
    def _make_witness_record(
        self,
        work_id: str,
        work_title: str,
        language_code: str,
        script_family: str,
        text_content: str,
        origin_class: str,
        source_uri: str,
        **optional_fields
    ) -> WitnessRecord:
        """
        Helper to construct a WitnessRecord from parsed fields.
        
        Handles hashing and default values.
        """
        import hashlib
        from ..core import License
        
        content_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()
        
        license_obj = License(
            code=optional_fields.pop("license_code", self.license_code),
            url=optional_fields.pop("license_url", None),
        )
        
        record = WitnessRecord(
            work_id=work_id,
            work_title=work_title,
            language_code=language_code,
            script_family=script_family,
            text_content=text_content,
            origin_class=origin_class,
            source_archive=self.archive_name,
            source_uri=source_uri,
            license=license_obj,
            content_hash=content_hash,
            acquisition_date=datetime.utcnow(),
            ingest_pipeline_version="0.1.0",
            **optional_fields
        )
        return record
