# The_Book/src/core/schema.py
# Unified Pydantic models for witness records and metadata

from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime
from enum import Enum
import json

class OriginClass(str, Enum):
    """Allowed witness origin classifications."""
    WITNESS = "witness"
    CRITICAL_EDITION_SOURCE_LANGUAGE = "critical_edition_source_language"
    TRANSLITERATION = "transliteration"
    DIPLOMATIC_TRANSCRIPTION = "diplomatic_transcription"

class ScriptFamily(str, Enum):
    """Supported script families."""
    HEBREW = "Hebrew"
    GREEK = "Greek"
    CUNEIFORM = "Cuneiform"
    EGYPTIAN_HIEROGLYPHIC = "Egyptian-Hieroglyphic"
    EGYPTIAN_HIERATIC = "Egyptian-Hieratic"
    EGYPTIAN_DEMOTIC = "Egyptian-Demotic"
    COPTIC = "Coptic"
    CYRILLIC = "Cyrillic"
    LATIN = "Latin"
    ARABIC = "Arabic"
    GEORGIAN = "Georgian"
    ARMENIAN = "Armenian"
    RUNNING_HAND = "Running-Hand"
    GOTHIC = "Gothic"
    RUNIC = "Runic"
    CJK = "CJK"

class TransliterationSystem(str, Enum):
    """Standard transliteration conventions."""
    BETACODE = "betacode"
    ATF = "atf"
    LEIDEN = "leiden"
    TRANSLITERATION_EN = "transliteration_en"
    NONE = "none"

class QAStatus(str, Enum):
    """Validation status."""
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"

class ConfidenceLevel(str, Enum):
    """Textual criticism confidence."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class CanonicalStatus(str, Enum):
    """Work canonical status."""
    CANONICAL = "canonical"
    DEUTEROCANON = "deuterocanon"
    APOCRYPHA = "apocrypha"
    DISPUTED = "disputed"

class License(BaseModel):
    """Structured license representation."""
    code: str
    url: Optional[str] = None
    attribution_required: bool = True
    derivative_works_allowed: bool = True
    share_alike_required: Optional[bool] = None

class WitnessRecord(BaseModel):
    """Core unified witness record schema."""
    
    # Identity & Classification
    work_id: str = Field(..., description="Canonical work ID from inventory")
    work_title: str = Field(..., description="Normalized work title")
    language_code: str = Field(..., description="ISO 639-3 code")
    script_family: ScriptFamily
    origin_class: OriginClass
    
    # Content
    text_content: str = Field(..., description="Full original-language text or transliteration")
    content_hash: str = Field(..., description="SHA-256 hash for dedup")
    
    # Source Attribution
    source_archive: str = Field(..., description="Archive name from sources.yaml")
    source_uri: str = Field(..., description="Persistent URL at source")
    license: License
    acquisition_date: datetime
    source_version_date: Optional[datetime] = None
    
    # Scholarly Metadata
    manuscript_siglum: Optional[str] = None
    witness_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    period: Optional[str] = None
    provenance: Optional[str] = None
    
    # Processing
    morphology_tagged: bool = False
    transliteration_system: Optional[TransliterationSystem] = None
    work_aliases: Optional[List[str]] = None
    notes: Optional[str] = None
    
    # QA & Tracking
    ingest_pipeline_version: str
    qa_validation_status: QAStatus = QAStatus.NEEDS_REVIEW
    dedup_match_group: Optional[str] = None
    quarantine_reason: Optional[str] = None
    export_included: bool = False
    
    def model_dump_json(self, **kwargs):
        """Override to use enum values."""
        return self.model_dump(mode='json', **kwargs)
    
    class Config:
        use_enum_values = False

class WorkInventoryEntry(BaseModel):
    """Canonical work entry from inventory files."""
    work_id: str
    canonical_title: str
    language_code: str
    script_family: ScriptFamily
    alternate_titles: List[str] = []
    expected_witness_families: List[str] = []
    confidence_level: CanonicalStatus = CanonicalStatus.CANONICAL
    notes: Optional[str] = None
    
    @field_validator("language_code")
    @classmethod
    def validate_language_code(cls, v):
        """Validate ISO 639-3 format (3 lowercase letters)."""
        if not (isinstance(v, str) and len(v) == 3 and v.islower() and v.isalpha()):
            raise ValueError(f"Invalid ISO 639-3 code: {v}")
        return v

class ArchiveConfig(BaseModel):
    """Configuration for a single archive source."""
    name: str
    domain: str
    url: str
    adapter_class: str
    format: str
    license: str
    parallel_workers: int = 2
    refresh_schedule: str = "monthly"
    v1_enabled: bool = True
    auth_required: Optional[bool] = False
    api_endpoint: Optional[str] = None
    oai_pmh_endpoint: Optional[str] = None
    search_query: Optional[str] = None
