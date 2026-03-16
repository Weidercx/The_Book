# The Book: Global Original-Language Canon Corpus

**Project Status**: Early Implementation (v0.1.0)

## Project Charter

The Book is a reproducible, origin-language-only digital corpus ingestion and normalization pipeline. It aggregates textual witnesses from global institutional archives (museums, national libraries, religious institutions, scholarly corpora) into a unified, machine-readable dataset.

**Core Principle**: Accept only original-language texts and scholarly representations thereof. All translations are excluded.

## Scope

### Included (v1)

**Biblical & Deuterocanon**
- Hebrew Bible: Open Scriptures Hebrew Bible (OSHB) with WLC witness
- Greek New Testament: SBLGNT + MACULA Greek linguistic annotations
- Aramaic portions (Daniel, Ezra): OSHB-provided tags
- Apocrypha & Deuterocanon: original-language witnesses only (DSS, LXX, Vetus Latina, etc.)

**Ancient & Classical**
- Sumerian & Akkadian: ORACC + CDLI (cuneiform ATF transliterations + artifacts)
- Egyptian: Trismegistos metadata layer + Coptic Scriptorium (post-Pharaonic Coptic religious texts)

**European Historical (Medieval & Modern Languages)**
- Old Church Slavonic, Old Norse, Medieval Latin, Old English: Transkribus API + CLARIN FCS
- Polish manuscripts: Polona (IIIF-compliant)
- German, Swedish, and broader European digitized texts: Deutsche Digitale Bibliothek, KB Digitalt aggregation

**Russian & Slavic**
- Russian texts (historical, Old Russian, Church Slavonic): Internet Archive Russian Collection (OAI-PMH)
- Russian State Library manuscripts: Aleph catalog (v1.5+ when access expanded)

**Ethiopian & Ge'ez**
- Ge'ez, Amharic, Ethiopic texts: Internet Archive Ethiopian Collection (OAI-PMH)

### Excluded (v1)

- All modern translations (except critical source editions in original language)
- Commentaries and paraphrases
- Image-only archives without OCR/machine-readable text
- Proprietary or unclear-license materials

## Data Model

All ingested records conform to a unified `WitnessRecord` schema with required and optional fields:

**Required Fields**
- `work_id`: Canonical work identifier
- `work_title`, `language_code`, `script_family`
- `text_content`, `content_hash` (SHA-256 for dedup)
- `origin_class`: witness | critical_edition_source_language | transliteration | diplomatic_transcription
- `source_archive`, `source_uri`, `license`, `acquisition_date`
- `ingest_pipeline_version`, `qa_validation_status`

**Optional Fields**
- `manuscript_siglum`, `witness_confidence`, `period`, `provenance`
- `morphology_tagged`, `transliteration_system`, `work_aliases`
- `source_version_date`, `notes`, `quarantine_reason`

See [`config/schema.yaml`](config/schema.yaml) and [`src/core/schema.py`](src/core/schema.py) for full schema definition.

## Policy Gates

All ingestion is controlled by hard policy enforcement:

1. **Origin-Class Gate**: Only witness, critical edition (source language), transliteration, or diplomatic transcription allowed.
2. **License Gate**: Records must have acceptable licenses (CC-BY-4.0, CC-BY-SA-3.0+, Public-Domain, CC0) with explicit license URL.
3. **Provenance Gate**: Mandatory source_archive, source_uri, acquisition_date, license.
4. **Language-Code Validation**: ISO 639-3 compliance.
5. **Unicode Normalization**: NFC by default; language-specific overrides (e.g., Hebrew uses NFD for diacritics).
6. **Deduplication**: Exact + fuzzy matching across archives; flagged for human review.

See [`config/rules.yaml`](config/rules.yaml) for detailed gate definitions.

## Architecture

### Directory Structure

```
The_Book/
├── config/
│   ├── sources.yaml         # Archive registry
│   ├── schema.yaml          # Unified witness record schema
│   └── rules.yaml           # Ingest policy gates
├── src/
│   ├── core/
│   │   ├── schema.py        # Pydantic models
│   │   └── policy.py        # Policy enforcement + validation
│   ├── adapters/            # Archive-specific parsers
│   ├── normalizers/         # Text cleanup, transliteration, Unicode
│   ├── validators/          # QA checks (schema, dedup, license)
│   └── exporters/           # Output serialization (JSONL, Parquet, etc.)
├── agents/                  # SDLC agent factory & agents
├── inventory/               # Canonical work inventories (YAML)
├── tests/                   # Unit + integration tests
└── docs/                    # Full documentation
```

### Agent-Based SDLC

The pipeline uses a factory-spawned pool of stateless agents:

- **IngestAgent**: Fetch + parse from one archive
- **SchemaAgent**: Normalize records to unified model
- **QAAgent**: Validate against policy gates
- **DedupAgent**: Fuzzy + exact deduplication
- **LicenseAgent**: License compliance gate (critical blocker)
- **GapReportAgent**: Compare ingested works vs canonical inventory
- **ExportAgent**: Serialize to JSONL, Parquet, catalog

Agents run in parallel where possible and report structured results.

See [`agents/factory.py`](agents/factory.py) for orchestration.

## Installation & Setup

### Requirements

- Python 3.10+
- System libraries: libxml2-dev, libxslt-dev, libicu-dev
- ICU4C (Unicode support): See [FONTS.md](FONTS.md#troubleshooting) for installation by OS
- **System Fonts** (required for text validation): SBL Hebrew, SBL Greek, Noto Sans Cuneiform, Noto CJK, DejaVu Sans

### font Installation

The project includes a comprehensive font verification and installation guide:

**See [`FONTS.md`](FONTS.md)** for:
- Complete font requirements by script family
- OS-specific installation instructions (macOS, Windows, Linux)
- Font download links with licensing information
- Troubleshooting (including PyICU compilation)

**Quick verification**:
```bash
# Check if all fonts + language handlers are installed
python scripts/verify_fonts.py
```

### Language Handlers

The project includes specialized Unicode/script detection and validation:

- **Script Detection** (via PyICU + Unicode ranges): Hebrew, Greek, Cyrillic, Arabic, Cuneiform, Egyptian, CJK, etc.
- **Language Detection** (via langdetect + ISO 639-3): Identifies language codes from text
- **Character Validation**: Detects encoding errors, control characters, script consistency
- **Font Coverage Checking**: Validates fonts cover required Unicode ranges

See [`src/handlers/language_handlers.py`](src/handlers/language_handlers.py) for API.

### Quick Start

```bash
# Clone repo
git clone https://github.com/...
cd The_Book

# Install Python dependencies
pip install -r requirements.txt

# Verify fonts + language handlers
python scripts/verify_fonts.py

# Run smoke tests
pytest tests/ -v

# (Upcoming) Run full ingest pipeline
python -m src.orchestration.pipeline
```

## Getting Started (Contributor Guide)

1. **Read the charter** above and [`ARCHITECTURE.md`](docs/ARCHITECTURE.md)
2. **Understand the schema** in [`config/schema.yaml`](config/schema.yaml)
3. **Check enabled archives** in [`config/sources.yaml`](config/sources.yaml)
4. **Add a new adapter**: Copy [`src/adapters/base_adapter.py`](src/adapters/base_adapter.py), implement `fetch()` and `parse()` methods
5. **Test locally**: `pytest tests/ -v`
6. **Run integration test**: `python -c "from agents import AgentFactory; ..."`

## Current Implementation Status

✅ Config files (sources.yaml, schema.yaml, rules.yaml)  
✅ Core schema (Pydantic models, enums)  
✅ Policy enforcement (origin-class, license, provenance gates)  
✅ Adapter base class  
✅ Agent base class + factory  
🔲 Specific adapters (OSHB, SBLGNT, ORACC, CDLI, Transkribus, etc.)  
🔲 Normalizers (Unicode, transliteration)  
🔲 Validators (schema, dedup, gap reporting)  
🔲 Exporters (JSONL, Parquet, catalog)  
🔲 Inventory files (Bible, cuneiform, Egyptian, etc.)  
🔲 Full integration tests  
🔲 Documentation (adapters guide, agent design patterns)  

## License

Project code: Apache 2.0 (unless otherwise noted)  
Ingested data: Per-source licensing (see provenance manifest in exports)

## Contact & Contributions

For questions, open an issue or contact the maintainers.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contributor guidelines.

