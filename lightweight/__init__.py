import sys
from pathlib import Path

"""Compatibility package for the LightWeight source tree.

This allows imports like `lightweight.hardware` to resolve to files 
inside the `cli/` directory even though they are technically separate.
"""

_pkg_dir = Path(__file__).resolve().parent
__path__ = [str(_pkg_dir)]

if getattr(sys, 'frozen', False):
    # Support for PyInstaller / frozen environments
    _base_dir = Path(sys._MEIPASS)
    # In some PyInstaller configs, cli might be at the root of the bundle
    _cli_dir = _base_dir / "cli"
    if _cli_dir.exists():
        __path__.append(str(_cli_dir))
else:
    # Standard development environment
    _legacy_src_dir = _pkg_dir.parent / "cli"
    if _legacy_src_dir.exists():
        __path__.append(str(_legacy_src_dir))
