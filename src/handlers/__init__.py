"""
Language and script handlers module.

Provides utilities for:
- Script family detection
- Language identification
- Character validation
- Font coverage checking
"""

from src.handlers.language_handlers import (
    CharacterValidator,
    FontValidator,
    LanguageDetector,
    ScriptDetector,
    ScriptRange,
    detect_language,
    detect_script,
    validate_text,
)

__all__ = [
    "ScriptDetector",
    "LanguageDetector",
    "CharacterValidator",
    "FontValidator",
    "ScriptRange",
    "detect_script",
    "detect_language",
    "validate_text",
]
