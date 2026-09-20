"""Main entry point for standalone EXE.

This module provides a simple main() function for PyInstaller packaging.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---- Fix sys.path BEFORE any eiw imports ----
# In the PyInstaller EXE bundle, the layout is:
#   _internal/
#     eiw/          ← the Python package
#   So we add _internal to sys.path so 'eiw.app' resolves.
# In dev mode (no _MEIPASS), add project_root/src so 'eiw.app' still resolves.
if getattr(sys, '_MEIPASS', None):
    bundle_root = Path(sys._MEIPASS)
    if str(bundle_root) not in sys.path:
        sys.path.insert(0, str(bundle_root))
else:
    # Running from source: src/eiw/__main__.py → project_root
    base = Path(__file__).parent.parent
    src_path = base / "src"
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


def main():
    """Run the Enterprise Data Agent application."""
    # Set up environment defaults for standalone mode
    if not os.getenv("EIW_DATABASE_URL"):
        os.environ["EIW_DATABASE_URL"] = "postgresql+psycopg://eiw:eiw@localhost:5432/eiw"

    if not os.getenv("EIW_ARTIFACT_ROOT"):
        os.environ["EIW_ARTIFACT_ROOT"] = os.path.join(os.path.dirname(sys.executable), "artifacts")

    # Create artifacts directory
    artifact_root = os.path.join(os.path.dirname(sys.executable), "artifacts")
    os.makedirs(artifact_root, exist_ok=True)

    # Run uvicorn server
    import uvicorn

    uvicorn.run(
        "eiw.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
