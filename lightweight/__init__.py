"""Compatibility package for the LightWeight source tree.

The project metadata and runtime imports expect a top-level ``lightweight``
package, while the current source files live under ``cli/``. Expose that
directory as part of this package path so imports like
``lightweight.hardware`` and ``lightweight.cli`` resolve consistently in
development, packaging, and PyInstaller builds.
"""

from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
_legacy_src_dir = _pkg_dir.parent / "cli"

# Let Python discover submodules from both this package directory and the
# existing legacy source tree.
__path__ = [str(_pkg_dir)]
if _legacy_src_dir.exists():
    __path__.append(str(_legacy_src_dir))

