"""
SEU Authentication Library
"""

from .auth_client import SEUAuthClient
from .auth_manager import SEUAuthManager

__version__ = "0.1.0"
__all__ = [
    # auth_client
    "SEUAuthClient",
    # auth_manager
    "SEUAuthManager",
]
