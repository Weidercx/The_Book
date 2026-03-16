# Font Installation Guide

## Overview

The Book corpus project requires system-level font installation for proper rendering and validation of original-language texts across multiple scripts. These fonts are **not** Python packages—they must be installed on your operating system.

## Required Fonts by Script Family

### Hebrew (heb) & Aramaic (arc, ajp)
- **SBL Hebrew** (SBLHebrw.ttf) — Scholarly standard for Biblical Hebrew
  - License: Free for academic/personal use
  - Download: https://www.sbl-site.org/Fonts/SBLHebrewFont.zip
  - Includes: Ancient Hebrew, diacritical marks, cantillation

### Greek (grc, ell)
- **SBL Greek Glyphs** (SBLGreek.ttf) — Standard for Koine Greek
  - License: Free for academic/personal use
  - Download: https://www.sbl-site.org/Fonts/SBLGreekFont.zip
  - Includes: Polytonic diacritics, breathing marks, iota subscript

### Cuneiform (akk, sux-Xsux)
- **Noto Sans Cuneiform** (NotoSansCuneiform-Regular.ttf)
  - License: OFL (Open Font License)
  - Download: https://fonts.google.com/noto/specimen/Noto+Sans+Cuneiform
  - Includes: Sumero-Akkadian wedge script

### Egyptian (egy, cop)
- **Noto Sans Egyptian Hieroglyphs** (NotoSansEgyptianHieroglyphs-Regular.ttf)
  - License: OFL
  - Download: https://fonts.google.com/noto/specimen/Noto+Sans+Egyptian+Hieroglyphs
  - Includes: Hieroglyphic, hieratic, demotic Unicode ranges
  
- **Scheherazade** (SchehDoctEOL.ttf) — Arabic/Coptic support
  - License: OFL
  - Download: https://software.sil.org/scheherazade/

### CJK Scripts (zho, jpn, kor)
- **Noto Sans CJK** (NotoSansCJK-*.ttf family)
  - License: OFL
  - Download: https://fonts.google.com/noto/specimen/Noto+Sans+CJK+JP
  - Includes: Simplified/Traditional Chinese, Japanese, Korean

### Cyrillic (rus, chu, mkd, srp)
- **DejaVu Sans** (DejaVuSans.ttf) — Comprehensive Cyrillic + Latin
  - License: OFL
  - Download: https://dejavu-fonts.github.io/
  - Includes: Old Church Slavonic extensions via Unicode
  
- **Liberation Serif** (LiberationSerif-Regular.ttf)
  - License: OFL
  - Download: https://github.com/liberationfonts/liberation-fonts

### Georgian (kat) & Armenian (hye)
- **Noto Sans Georgian** (NotoSansGeorgian-*.ttf)
  - License: OFL
  - Download: https://fonts.google.com/noto/specimen/Noto+Sans+Georgian
  
- **Noto Sans Armenian** (NotoSansArmenian-*.ttf)
  - License: OFL
  - Download: https://fonts.google.com/noto/specimen/Noto+Sans+Armenian

### Old Church Slavonic (chu)
- **Fedra Sans** or **DejaVu Sans** with Unicode extensions
- Unicode block: Cyrillic Extended-A/B (U+0460–U+052F)

### Gothic (got)
- Any font with **Deseret Alphabet** support (rarely printed; use transliteration)
- Or use specialized Gothic paleography fonts for manuscript images

---

## Installation Instructions by Operating System

### macOS

```bash
# Using Homebrew Cask (easiest)
brew install font-sbl-hebrew
brew install font-sbl-greek
brew install font-noto-sans-cuneiform
brew install font-noto-sans-cjk
brew install font-noto-sans-georgian
brew install font-noto-sans-armenian
brew install font-dejavu-sans

# Or manual: Download .ttf files from links above and double-click to install
# They will be added to: ~/Library/Fonts/
```

### Windows (10/11)

**Method 1: Drag-and-drop**
1. Download .ttf files from links above
2. Right-click on .ttf file → "Install font"
   - For all users: Admin required; goes to C:\Windows\Fonts\
   - For current user: C:\Users\<username>\AppData\Local\Microsoft\Windows\Fonts\

**Method 2: PowerShell (Admin)**
```powershell
# Create fonts directory
New-Item -ItemType Directory -Path "C:\Fonts" -Force

# Copy downloaded fonts there
Copy-Item -Path "C:\Downloads\*.ttf" -Destination "C:\Fonts\"

# Register fonts
Get-ChildItem "C:\Fonts\*.ttf" | ForEach-Object {
    Copy-Item $_.FullName -Destination "C:\Windows\Fonts\"
}
```

### Linux (Ubuntu/Debian)

```bash
# System-wide fonts
sudo mkdir -p /usr/share/fonts/custom
sudo cp ~/Downloads/*.ttf /usr/share/fonts/custom/
sudo fc-cache -fv

# User-local fonts
mkdir -p ~/.local/share/fonts
cp ~/Downloads/*.ttf ~/.local/share/fonts/
fc-cache -fv ~/.local/share/fonts/
```

### Linux (Fedora/RHEL)

```bash
sudo mkdir -p /usr/share/fonts/custom
sudo cp ~/Downloads/*.ttf /usr/share/fonts/custom/
sudo dnf install fontconfig
sudo fc-cache -fv
```

---

## Verification

### Python Script to Verify Font Installation

```python
# scripts/verify_fonts.py
from fontTools.ttLib import TTFont
import icu
from pathlib import Path

REQUIRED_FONTS = {
    "SBL Hebrew": ["SBLHebrw.ttf"],
    "SBL Greek": ["SBLGreek.ttf"],
    "Noto Sans Cuneiform": ["NotoSansCuneiform-Regular.ttf"],
    "Noto Sans CJK": ["NotoSansCJK-Regular.ttc"],
    "DejaVu Sans": ["DejaVuSans.ttf"],
}

FONT_PATHS = [
    Path.home() / "Library" / "Fonts",  # macOS
    Path("C:\\Windows\\Fonts"),  # Windows
    Path.home() / ".local" / "share" / "fonts",  # Linux user
    Path("/usr/share/fonts"),  # Linux system
]

def check_fonts():
    found = {}
    missing = {}
    
    for family, filenames in REQUIRED_FONTS.items():
        for filename in filenames:
            for font_path in FONT_PATHS:
                full_path = font_path / filename
                if full_path.exists():
                    font = TTFont(str(full_path))
                    found[family] = str(full_path)
                    break
            else:
                missing[family] = filenames
    
    print(f"✓ Found {len(found)} fonts:")
    for family, path in found.items():
        print(f"  {family}: {path}")
    
    if missing:
        print(f"\n✗ Missing {len(missing)} fonts:")
        for family, files in missing.items():
            print(f"  {family}: {files}")
        return False
    
    return True

if __name__ == "__main__":
    success = check_fonts()
    exit(0 if success else 1)
```

---

## Unicode Character Coverage

Fonts are verified to cover these Unicode blocks:

| Script | CodeBlock | Range | Font |
|--------|-----------|-------|------|
| Hebrew | Hebrew | U+0590–U+05FF | SBL Hebrew |
| Greek | Greek & Coptic | U+0370–U+03FF | SBL Greek |
| Cyrillic | Cyrillic | U+0400–U+04FF | DejaVu Sans |
| Cuneiform | Cuneiform | U+12000–U+123FF | Noto Sans Cuneiform |
| Egyptian | Egyptian Hieros | U+13000–U+1342F | Noto Sans Egyptian Hieroglyphs |
| CJK | CJK Unified | U+4E00–U+9FFF | Noto Sans CJK |
| Georgian | Georgian | U+10A0–U+10FF | Noto Sans Georgian |
| Armenian | Armenian | U+0530–U+058F | Noto Sans Armenian |

---

## Troubleshooting

### Font not rendering in terminal
- Ensure terminal emulator supports the font (e.g., VS Code, iTerm2, Windows Terminal)
- Some fonts require separate installation of font rendering libraries (fontconfig on Linux)

### PyICU fails on install
- **macOS**: `brew install icu4c` then set `ICU4C_PATH=$(brew --prefix icu4c)`
- **Windows**: Download ICU binaries from https://github.com/unicode-org/icu/releases
- **Linux**: `sudo apt install libicu-dev` (Ubuntu) or `sudo dnf install libicu-devel` (Fedora)

### Font validation fails in Python
```bash
pip show fonttools
pip show PyICU

# Reinstall if needed
pip install --upgrade fonttools PyICU
```

---

## References

- SBL Fonts: https://www.sbl-site.org/Fonts/
- Noto Fonts: https://fonts.google.com/noto
- fontTools: https://github.com/fonttools/fonttools
- PyICU: https://pypi.org/project/PyICU/
