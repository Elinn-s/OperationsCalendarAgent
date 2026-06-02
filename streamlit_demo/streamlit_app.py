from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Keep the current Streamlit UI behavior while exposing a clearer frontend entry.
# The existing pages still use Streamlit's pages/ discovery.
import main  # noqa: F401
