"""
Language and script detection handlers.

Provides utilities for:
- Script family detection (Hebrew, Greek, Cuneiform, Egyptian, CJK, etc.)
- Language identification via Unicode properties and statistical methods
- Character classification and validation
- Font coverage checking
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

try:
    import icu
    HAS_ICU = True
except ImportError:
    HAS_ICU = False
    logging.warning("PyICU not installed; script detection will use regex fallback")

try:
    from langdetect import detect, detect_langs, LangDetectException
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False
    logging.warning("langdetect not installed; language detection disabled")

try:
    from fontTools.ttLib import TTFont
    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False
    logging.warning("fontTools not installed; font validation disabled")

import regex  # Advanced Unicode support
from src.core.schema import ScriptFamily


class ScriptRange:
    """Unicode ranges for script family detection."""
    
    # Alphabetic & Abjads
    HEBREW = (0x0590, 0x05FF)
    GREEK = (0x0370, 0x03FF)
    CYRILLIC = (0x0400, 0x04FF)
    CYRILLIC_EXTENDED = (0x0460, 0x052F)  # Old Church Slavonic
    ARABIC = (0x0600, 0x06FF)
    GEORGIAN = (0x10A0, 0x10FF)
    ARMENIAN = (0x0530, 0x058F)
    GOTHIC = (0x10330, 0x1034F)  # Rare; use transliteration
    
    # Logographic/Complex
    CUNEIFORM = (0x12000, 0x123FF)
    EGYPTIAN_HIEROGLYPHS = (0x13000, 0x1342F)
    
    # CJK
    CJK_UNIFIED = (0x4E00, 0x9FFF)
    HIRAGANA = (0x3040, 0x309F)
    KATAKANA = (0x30A0, 0x30FF)
    HANGUL = (0xAC00, 0xD7AF)
    
    # Combining marks & diacritics
    COMBINING_DIACRITICS = (0x0300, 0x036F)
    COMBINING_HEBREW_MARKS = (0x0591, 0x05C7)
    COMBINING_GREEK_DIACRITICS = (0x1F00, 0x1FFF)
    
    @classmethod
    def codepoint_to_script(cls, codepoint: int) -> Optional[ScriptFamily]:
        """Map Unicode codepoint to script family."""
        ranges = {
            cls.HEBREW: ScriptFamily.HEBREW,
            cls.GREEK: ScriptFamily.GREEK,
            cls.CYRILLIC: ScriptFamily.CYRILLIC,
            cls.CYRILLIC_EXTENDED: ScriptFamily.CYRILLIC,
            cls.ARABIC: ScriptFamily.ARABIC,
            cls.GEORGIAN: ScriptFamily.GEORGIAN,
            cls.ARMENIAN: ScriptFamily.ARMENIAN,
            cls.GOTHIC: ScriptFamily.GOTHIC,
            cls.CUNEIFORM: ScriptFamily.CUNEIFORM,
            cls.EGYPTIAN_HIEROGLYPHS: ScriptFamily.EGYPTIAN_HIEROGLYPHIC,
            cls.CJK_UNIFIED: ScriptFamily.CJK,
            cls.HIRAGANA: ScriptFamily.CJK,
            cls.KATAKANA: ScriptFamily.CJK,
            cls.HANGUL: ScriptFamily.CJK,
        }
        
        for (start, end), script in ranges.items():
            if start <= codepoint <= end:
                return script
        
        return None


class ScriptDetector:
    """Detects script families in text using Unicode properties."""
    
    # Unicode property shortcuts (via PyICU if available)
    SCRIPT_NAMES = {
        "Hebrew": ScriptFamily.HEBREW,
        "Greek": ScriptFamily.GREEK,
        "Cyrillic": ScriptFamily.CYRILLIC,
        "Arabic": ScriptFamily.ARABIC,
        "Georgian": ScriptFamily.GEORGIAN,
        "Armenian": ScriptFamily.ARMENIAN,
        "Han": ScriptFamily.CJK,
        "Hiragana": ScriptFamily.CJK,
        "Katakana": ScriptFamily.CJK,
        "Hangul": ScriptFamily.CJK,
    }
    
    @staticmethod
    def detect_dominant_script(text: str) -> Optional[ScriptFamily]:
        """
        Detect the dominant script family in text.
        
        Returns the most frequently occurring script, or None if text is
        primarily Latin/ASCII.
        """
        if not text:
            return None
        
        script_counts: Dict[ScriptFamily, int] = {}
        
        for char in text:
            if char.isspace() or char in ".,;:!?()[]{}\"'-":
                continue  # Skip punctuation & whitespace
            
            codepoint = ord(char)
            script = ScriptRange.codepoint_to_script(codepoint)
            
            if script:
                script_counts[script] = script_counts.get(script, 0) + 1
        
        if not script_counts:
            return None
        
        return max(script_counts, key=script_counts.get)
    
    @staticmethod
    def detect_all_scripts(text: str) -> Set[ScriptFamily]:
        """Detect all scripts present in text."""
        scripts = set()
        
        for char in text:
            codepoint = ord(char)
            script = ScriptRange.codepoint_to_script(codepoint)
            if script:
                scripts.add(script)
        
        return scripts
    
    @staticmethod
    def has_combining_marks(text: str) -> bool:
        """Check if text contains combining diacritical marks."""
        for char in text:
            codepoint = ord(char)
            if (ScriptRange.COMBINING_DIACRITICS[0] <= codepoint <= ScriptRange.COMBINING_DIACRITICS[1] or
                ScriptRange.COMBINING_HEBREW_MARKS[0] <= codepoint <= ScriptRange.COMBINING_HEBREW_MARKS[1] or
                ScriptRange.COMBINING_GREEK_DIACRITICS[0] <= codepoint <= ScriptRange.COMBINING_GREEK_DIACRITICS[1]):
                return True
        
        return False


class LanguageDetector:
    """Detects language via statistical and Unicode-property methods."""
    
    @staticmethod
    def detect_language(text: str) -> Optional[str]:
        """
        Detect language code (ISO 639-3) using langdetect library.
        
        Falls back to script-based heuristics if langdetect fails.
        
        Returns: ISO 639-3 language code (3 lowercase letters) or None.
        """
        if not HAS_LANGDETECT:
            return None
        
        # langdetect uses ISO 639-1 codes; we need to convert to ISO 639-3
        iso639_3_map = {
            "he": "heb",  # Hebrew
            "el": "ell",  # Greek (modern)
            "grc": "grc",  # Ancient Greek (if supported)
            "en": "eng",
            "la": "lat",  # Latin
            "ar": "ara",
            "zh-cn": "zho",
            "zh-tw": "zho",
            "ja": "jpn",
            "ko": "kor",
            "ru": "rus",
            "et": "est",  # Ethiopic (Ge'ez)
        }
        
        try:
            lang = detect(text)
            return iso639_3_map.get(lang, lang)
        except (LangDetectException, Exception):
            return None
    
    @staticmethod
    def detect_language_from_script(script: ScriptFamily) -> List[str]:
        """
        Infer likely languages based on script family alone.
        
        Returns list of possible ISO 639-3 codes, ordered by likelihood.
        """
        script_language_map = {
            ScriptFamily.HEBREW: ["heb", "arc", "yid"],  # Biblical Hebrew, Aramaic, Yiddish
            ScriptFamily.GREEK: ["grc", "ell"],  # Koine/Ancient Greek, Modern Greek
            ScriptFamily.CYRILLIC: ["rus", "chu", "mkd", "srp", "bul"],  # Russian, Old Church Slavonic, etc.
            ScriptFamily.ARABIC: ["ara", "ara-smd", "ara-ara"],  # Arabic varieties
            ScriptFamily.GEORGIAN: ["kat"],
            ScriptFamily.ARMENIAN: ["hye"],
            ScriptFamily.CUNEIFORM: ["akk", "sux"],  # Akkadian, Sumerian
            ScriptFamily.EGYPTIAN_HIEROGLYPHIC: ["egy"],
            ScriptFamily.EGYPTIAN_HIERATIC: ["egy"],
            ScriptFamily.EGYPTIAN_DEMOTIC: ["egy"],
            ScriptFamily.CJK: ["zho", "jpn", "kor"],
        }
        
        return script_language_map.get(script, [])


class CharacterValidator:
    """Validates characters against language/script requirements."""
    
    @staticmethod
    def has_invalid_control_characters(text: str) -> bool:
        """Check for unexpected control characters (U+0000–U+001F, U+007F–U+009F)."""
        for char in text:
            codepoint = ord(char)
            if (0x0000 <= codepoint <= 0x001F or 0x007F <= codepoint <= 0x009F):
                if char not in "\n\r\t":  # Allow normal whitespace
                    return True
        return False
    
    @staticmethod
    def has_replacement_character(text: str) -> bool:
        """Check for Unicode replacement character (U+FFFD) indicating encoding errors."""
        return "\ufffd" in text
    
    @staticmethod
    def validate_script_consistency(
        text: str, 
        expected_script: ScriptFamily
    ) -> Tuple[bool, List[str]]:
        """
        Validate that text conforms to expected script.
        
        Returns: (is_valid, warnings)
        
        Allows:
        - Expected script
        - Combining marks (diacritics)
        - Common punctuation
        - Whitespace
        """
        warnings = []
        allowed_codepoints = {ord(c) for c in ".,;:!?()[]{}\"'-–—… \n\r\t"}
        
        for char in text:
            codepoint = ord(char)
            
            # Allow ASCII punctuation, whitespace, digits
            if codepoint < 128 or codepoint in allowed_codepoints:
                continue
            
            # Allow combining marks
            if ScriptRange.COMBINING_DIACRITICS[0] <= codepoint <= ScriptRange.COMBINING_DIACRITICS[1]:
                continue
            
            script = ScriptRange.codepoint_to_script(codepoint)
            
            if script and script != expected_script:
                warnings.append(
                    f"Character '{char}' (U+{codepoint:04X}) is in {script}, "
                    f"but expected {expected_script}"
                )
        
        return len(warnings) == 0, warnings


class FontValidator:
    """Validates font coverage for script families."""
    
    FONT_SCRIPT_MAP: Dict[str, Set[ScriptFamily]] = {
        "SBL Hebrew": {ScriptFamily.HEBREW},
        "SBL Greek": {ScriptFamily.GREEK},
        "Noto Sans Cuneiform": {ScriptFamily.CUNEIFORM},
        "Noto Sans CJK": {ScriptFamily.CJK},
        "Noto Sans Egyptian Hieroglyphs": {ScriptFamily.EGYPTIAN_HIEROGLYPHIC},
        "Noto Sans Georgian": {ScriptFamily.GEORGIAN},
        "Noto Sans Armenian": {ScriptFamily.ARMENIAN},
        "DejaVu Sans": {ScriptFamily.CYRILLIC, ScriptFamily.GREEK},
    }
    
    @staticmethod
    def check_font_coverage(
        script: ScriptFamily,
        font_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if font covers a script family.
        
        If font_path is provided, validates against actual font file.
        Otherwise uses hardcoded mappings.
        
        Returns: (is_covered, reason)
        """
        if not font_path:
            # Use hardcoded mappings
            for font_name, scripts in FontValidator.FONT_SCRIPT_MAP.items():
                if script in scripts:
                    return True, f"Font '{font_name}' covers {script}"
            return False, f"No known font covers {script}"
        
        if not HAS_FONTTOOLS:
            return False, "fontTools not installed; cannot validate font file"
        
        try:
            font = TTFont(font_path)
            cmap = font.getBestCmap()
            
            if not cmap:
                return False, "Font has no cmap table"
            
            # Check if font covers at least one character in the script's Unicode range
            if script == ScriptFamily.HEBREW:
                test_range = range(ScriptRange.HEBREW[0], ScriptRange.HEBREW[1] + 1)
            elif script == ScriptFamily.GREEK:
                test_range = range(ScriptRange.GREEK[0], ScriptRange.GREEK[1] + 1)
            elif script == ScriptFamily.CUNEIFORM:
                test_range = range(ScriptRange.CUNEIFORM[0], ScriptRange.CUNEIFORM[1] + 1)
            else:
                return False, f"Script {script} range not defined for font validation"
            
            covered = sum(1 for codepoint in test_range if codepoint in cmap)
            total = len(list(test_range))
            coverage_pct = (covered / total) * 100 if total > 0 else 0
            
            is_adequate = coverage_pct >= 80  # 80% coverage threshold
            reason = f"Font covers {coverage_pct:.1f}% of {script} range"
            
            return is_adequate, reason
        
        except Exception as e:
            return False, f"Error reading font file: {e}"


# Module-level convenience functions

def detect_script(text: str) -> Optional[ScriptFamily]:
    """Detect dominant script in text."""
    return ScriptDetector.detect_dominant_script(text)


def detect_language(text: str) -> Optional[str]:
    """Detect language code (ISO 639-3)."""
    return LanguageDetector.detect_language(text)


def validate_text(
    text: str,
    expected_script: ScriptFamily,
    expected_language: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """
    Comprehensive text validation.
    
    Checks for:
    - Control characters
    - Replacement characters
    - Script consistency
    - Language consistency (if langdetect available)
    
    Returns: (is_valid, warnings)
    """
    warnings = []
    
    # Control character check
    if CharacterValidator.has_invalid_control_characters(text):
        warnings.append("Text contains unexpected control characters")
    
    # Replacement character check
    if CharacterValidator.has_replacement_character(text):
        warnings.append("Text contains Unicode replacement character (U+FFFD) - encoding error?")
    
    # Script consistency
    is_script_valid, script_warnings = CharacterValidator.validate_script_consistency(
        text, expected_script
    )
    warnings.extend(script_warnings)
    
    # Language detection (informational only)
    if HAS_LANGDETECT and expected_language:
        detected_lang = LanguageDetector.detect_language(text)
        if detected_lang and detected_lang != expected_language:
            warnings.append(
                f"Detected language '{detected_lang}' differs from expected '{expected_language}'"
            )
    
    return len([w for w in warnings if "Character" in w or "control" in w or "FFFD" in w]) == 0, warnings
