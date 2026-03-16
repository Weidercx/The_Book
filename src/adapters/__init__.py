# The_Book/src/adapters/__init__.py

from .base_adapter import BaseAdapter
from .dss_adapter import DSSGenesisTranscriptionAdapter
from .hebrew_transcription_adapter import HebrewGenesisTranscriptionAdapter
from .oshb_adapter import OSHBGenesisAdapter
from .sefaria_adapter import SefariaGenesisAdapter

__all__ = [
    "BaseAdapter",
    "DSSGenesisTranscriptionAdapter",
    "HebrewGenesisTranscriptionAdapter",
    "OSHBGenesisAdapter",
    "SefariaGenesisAdapter",
]
