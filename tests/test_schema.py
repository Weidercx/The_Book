# The_Book/tests/test_schema.py
# Smoke tests for core schema validation

import pytest
from datetime import datetime
from src.core import (
    WitnessRecord, 
    License, 
    OriginClass, 
    ScriptFamily, 
    QAStatus, 
    IngestPolicy
)

class TestWitnessRecordSchema:
    """Test WitnessRecord schema validation."""
    
    def test_minimal_witness_record(self):
        """Create minimal valid WitnessRecord."""
        license_obj = License(
            code="CC-BY-4.0",
            url="https://creativecommons.org/licenses/by/4.0/",
        )
        
        record = WitnessRecord(
            work_id="bible.ot.genesis",
            work_title="Genesis",
            language_code="heb",
            script_family=ScriptFamily.HEBREW,
            text_content="בראשית",
            origin_class=OriginClass.WITNESS,
            source_archive="oshb",
            source_uri="https://github.com/openscriptures/morphhb",
            license=license_obj,
            content_hash="abc123",
            acquisition_date=datetime.utcnow(),
            ingest_pipeline_version="0.1.0",
        )
        
        assert record.work_id == "bible.ot.genesis"
        assert record.language_code == "heb"
        assert record.origin_class == OriginClass.WITNESS
    
    def test_invalid_language_code(self):
        """Invalid ISO 639-3 code should fail validation."""
        license_obj = License(code="CC-BY-4.0")
        
        with pytest.raises(ValueError):
            WitnessRecord(
                work_id="bible.ot.genesis",
                work_title="Genesis",
                language_code="hebrew",  # Invalid: should be 3-char code
                script_family=ScriptFamily.HEBREW,
                text_content="test",
                origin_class=OriginClass.WITNESS,
                source_archive="oshb",
                source_uri="https://example.com",
                license=license_obj,
                content_hash="abc123",
                acquisition_date=datetime.utcnow(),
                ingest_pipeline_version="0.1.0",
            )

class TestIngestPolicy:
    """Test policy enforcement gates."""
    
    def test_policy_accepts_valid_origin_class(self):
        """Valid origin classes pass gate."""
        license_obj = License(code="CC-BY-4.0", url="https://example.com")
        record = WitnessRecord(
            work_id="test", work_title="Test", language_code="heb",
            script_family=ScriptFamily.HEBREW, text_content="text",
            origin_class=OriginClass.WITNESS,
            source_archive="test", source_uri="https://example.com",
            license=license_obj, content_hash="abc",
            acquisition_date=datetime.utcnow(),
            ingest_pipeline_version="0.1.0",
        )
        
        is_valid, msg = IngestPolicy.validate_origin_class(record)
        assert is_valid
    
    def test_policy_accepts_valid_license(self):
        """Valid license passes gate."""
        license_obj = License(
            code="CC-BY-4.0",
            url="https://creativecommons.org/licenses/by/4.0/",
        )
        record = WitnessRecord(
            work_id="test", work_title="Test", language_code="heb",
            script_family=ScriptFamily.HEBREW, text_content="text",
            origin_class=OriginClass.WITNESS,
            source_archive="test", source_uri="https://example.com",
            license=license_obj, content_hash="abc",
            acquisition_date=datetime.utcnow(),
            ingest_pipeline_version="0.1.0",
        )
        
        is_valid, msg = IngestPolicy.validate_license(record)
        assert is_valid
    
    def test_policy_rejects_unknown_license(self):
        """Unknown license fails gate."""
        license_obj = License(
            code="UNKNOWN-LICENSE",
            url="https://example.com",
        )
        record = WitnessRecord(
            work_id="test", work_title="Test", language_code="heb",
            script_family=ScriptFamily.HEBREW, text_content="text",
            origin_class=OriginClass.WITNESS,
            source_archive="test", source_uri="https://example.com",
            license=license_obj, content_hash="abc",
            acquisition_date=datetime.utcnow(),
            ingest_pipeline_version="0.1.0",
        )
        
        is_valid, msg = IngestPolicy.validate_license(record)
        assert not is_valid
