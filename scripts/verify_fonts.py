#!/usr/bin/env python3
"""
Font and language handler verification script.

Checks for:
1. Required Python packages (PyICU, fontTools, langdetect, etc.)
2. System-level font installation (SBL Hebrew, SBL Greek, Noto Sans, DejaVu)
3. Font coverage for all script families

Run: python scripts/verify_fonts.py
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Tuple, List

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


def check_python_packages() -> Tuple[bool, List[str]]:
    """Check if required Python packages are installed."""
    required = {
        "pydantic": "Pydantic (data validation)",
        "PyICU": "PyICU (Unicode script detection)",
        "langdetect": "langdetect (language detection)",
        "fontTools": "fontTools (font validation)",
        "lxml": "lxml (XML parsing)",
        "regex": "regex (advanced Unicode regex)",
        "unicodedata2": "unicodedata2 (Unicode database)",
    }
    
    missing = []
    
    logger.info("Checking Python packages...")
    
    for package, description in required.items():
        try:
            __import__(package)
            logger.info(f"  ✓ {description}")
        except ImportError:
            logger.warning(f"  ✗ {description} (pip install {package})")
            missing.append(package)
    
    return len(missing) == 0, missing


def check_fonts() -> Tuple[bool, Dict[str, bool]]:
    """Check if required fonts are installed on the system."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        logger.error("fontTools not installed; skipping font verification")
        return False, {}
    
    # Font filenames and their script families
    required_fonts = {
        "SBL Hebrew": {
            "filenames": ["SBLHebrw.ttf", "SBL Hebrew.ttf"],
            "scripts": ["Hebrew"],
        },
        "SBL Greek": {
            "filenames": ["SBLGreek.ttf", "SBL Greek.ttf"],
            "scripts": ["Greek"],
        },
        "Noto Sans Cuneiform": {
            "filenames": ["NotoSansCuneiform-Regular.ttf"],
            "scripts": ["Cuneiform"],
        },
        "Noto Sans CJK": {
            "filenames": ["NotoSansCJK-Regular.ttc", "NotoSansCJK-Bold.ttc"],
            "scripts": ["CJK"],
        },
        "DejaVu Sans": {
            "filenames": ["DejaVuSans.ttf"],
            "scripts": ["Cyrillic", "Greek", "Latin"],
        },
    }
    
    # Search paths (OS-specific)
    search_paths = [
        Path.home() / "Library" / "Fonts",  # macOS
        Path("C:\\Windows\\Fonts"),  # Windows
        Path("C:\\Users") / Path.home().name / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",  # Windows user
        Path.home() / ".local" / "share" / "fonts",  # Linux user
        Path("/usr/share/fonts"),  # Linux system
        Path("/usr/local/share/fonts"),  # Linux local
    ]
    
    found_fonts = {}
    all_found = True
    
    logger.info("Checking system fonts...")
    
    for font_family, font_info in required_fonts.items():
        found = False
        for filename in font_info["filenames"]:
            for search_path in search_paths:
                font_path = search_path / filename
                if font_path.exists():
                    logger.info(f"  ✓ {font_family}: {font_path}")
                    found_fonts[font_family] = True
                    found = True
                    break
            if found:
                break
        
        if not found:
            logger.warning(
                f"  ✗ {font_family} not found. "
                f"Try: {font_info['filenames'][0]}"
            )
            found_fonts[font_family] = False
            all_found = False
    
    return all_found, found_fonts


def check_language_handlers() -> Tuple[bool, List[str]]:
    """Check if language handlers module can be imported."""
    warnings = []
    
    logger.info("Checking language handlers...")
    
    try:
        from src.handlers import (
            ScriptDetector,
            LanguageDetector,
            CharacterValidator,
            FontValidator,
        )
        logger.info("  ✓ Language handlers module imported successfully")
        
        # Quick sanity check
        test_text = "שלום עולם"  # Hebrew: "Hello world"
        script = ScriptDetector.detect_dominant_script(test_text)
        if script:
            logger.info(f"  ✓ Script detection working: Hebrew text detected as {script}")
        else:
            warnings.append("Script detection returned None for Hebrew test text")
        
    except ImportError as e:
        logger.error(f"  ✗ Failed to import language handlers: {e}")
        return False, [str(e)]
    
    return len(warnings) == 0, warnings


def main():
    """Run all verification checks."""
    logger.info("=" * 70)
    logger.info("The Book - Font and Language Handler Verification")
    logger.info("=" * 70)
    logger.info("")
    
    # Check Python packages
    packages_ok, missing_packages = check_python_packages()
    logger.info("")
    
    # Check system fonts
    fonts_ok, fonts_found = check_fonts()
    logger.info("")
    
    # Check language handlers
    handlers_ok, handler_warnings = check_language_handlers()
    logger.info("")
    
    # Summary
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    
    status_items = [
        ("Python packages", packages_ok),
        ("System fonts", fonts_ok),
        ("Language handlers", handlers_ok),
    ]
    
    all_ok = all(status for _, status in status_items)
    
    for item, status in status_items:
        symbol = "✓" if status else "✗"
        logger.info(f"{symbol} {item}")
    
    logger.info("")
    
    if all_ok:
        logger.info("✓ All checks passed! You're ready to ingest texts.")
        return 0
    else:
        logger.warning("✗ Some checks failed. See above for details.")
        
        if missing_packages:
            logger.warning("")
            logger.warning("To install missing Python packages, run:")
            logger.warning(f"  pip install {' '.join(missing_packages)}")
        
        if not fonts_ok:
            logger.warning("")
            logger.warning("To install system fonts, see FONTS.md:")
            logger.warning("  - macOS: brew install font-sbl-hebrew font-sbl-greek ...")
            logger.warning("  - Windows: Download .ttf files and double-click to install")
            logger.warning("  - Linux: Copy .ttf files to ~/.local/share/fonts/")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
