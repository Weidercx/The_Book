# The_Book/src/core/policy.py
# Origin-class validation and license compliance gates

import logging
from typing import List, Tuple, Dict
from .schema import WitnessRecord, OriginClass

logger = logging.getLogger(__name__)

class IngestPolicy:
    """Hard policy gates for witness ingestion."""
    
    ALLOWED_ORIGIN_CLASSES = {
        OriginClass.WITNESS,
        OriginClass.CRITICAL_EDITION_SOURCE_LANGUAGE,
        OriginClass.TRANSLITERATION,
        OriginClass.DIPLOMATIC_TRANSCRIPTION,
    }
    
    REJECTED_ORIGIN_CLASSES = {
        "translation",
        "paraphrase",
        "back_translation",
        "commentary_only",
        "study_bible",
    }
    
    ACCEPTABLE_LICENSES = {
        "CC-BY-4.0",
        "CC-BY-3.0",
        "CC-BY-SA-4.0",
        "CC-BY-SA-3.0",
        "Public-Domain",
        "CC0",
    }
    
    @staticmethod
    def validate_origin_class(record: WitnessRecord) -> Tuple[bool, str]:
        """
        Validate that origin_class is in allowed set.
        
        Returns: (is_valid, message)
        """
        if record.origin_class not in IngestPolicy.ALLOWED_ORIGIN_CLASSES:
            return False, f"Origin class {record.origin_class} not in allowed set."
        return True, "OK"
    
    @staticmethod
    def validate_license(record: WitnessRecord) -> Tuple[bool, str]:
        """
        Validate license compliance.
        
        Returns: (is_valid, message)
        For non-compliant licenses, record is not rejected but flagged for review.
        """
        if record.license.code not in IngestPolicy.ACCEPTABLE_LICENSES:
            return False, f"License {record.license.code} requires review; not in acceptable list."
        
        if record.license.url is None:
            return False, "License URL is required but missing."
        
        return True, "OK"
    
    @staticmethod
    def validate_provenance(record: WitnessRecord) -> Tuple[bool, str]:
        """
        Validate that provenance fields are present and non-empty.
        
        Returns: (is_valid, message)
        """
        if not record.source_archive:
            return False, "Required provenance field missing: source_archive"
        if not record.source_uri:
            return False, "Required provenance field missing: source_uri"
        if not record.acquisition_date:
            return False, "Required provenance field missing: acquisition_date"
        if not record.license:
            return False, "Required provenance field missing: license"
        return True, "OK"
    
    @staticmethod
    def check_ingest_gates(record: WitnessRecord) -> Dict[str, Tuple[bool, str]]:
        """Run all policy gates and return aggregated results."""
        results = {
            "origin_class": IngestPolicy.validate_origin_class(record),
            "license": IngestPolicy.validate_license(record),
            "provenance": IngestPolicy.validate_provenance(record),
        }
        
        failed = [k for k, (is_valid, msg) in results.items() if not is_valid]
        if failed:
            logger.warning(f"Record {record.work_id} failed gates: {failed}")
        
        return results
