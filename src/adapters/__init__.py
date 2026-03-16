# The_Book/src/adapters/__init__.py

from .base_adapter import BaseAdapter
from .oshb_adapter import OSHBGenesisAdapter
from .sefaria_adapter import SefariaGenesisAdapter

__all__ = ["BaseAdapter", "OSHBGenesisAdapter", "SefariaGenesisAdapter"]
