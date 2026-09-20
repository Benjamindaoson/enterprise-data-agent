"""Build script for Enterprise Data Agent EXE.

Usage:
    python scripts/build_exe.py          # Build EXE
    python scripts/build_exe.py --clean  # Clean and rebuild
"""

from __future__ import annotations

import os
import sys
import shutil
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Build Enterprise Data Agent EXE")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts first")
    parser.add_argument("--output", default="dist", help="Output directory")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    output_dir = project_root / args.output
    spec_file = project_root / "eiw.spec"
    dist_dir = output_dir / "EnterpriseDataAgent"

    # Clean if requested
    if args.clean:
        print("Cleaning build artifacts...")
        for path in [project_root / "build", output_dir]:
            if path.exists():
                shutil.rmtree(path)
                print(f"  Removed: {path}")

    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        os.system("pip install pyinstaller")

    # Ensure other dependencies
    print("Checking dependencies...")
    os.system("pip install -e .")

    # Build
    print(f"\nBuilding EXE...")
    print(f"  Spec file: {spec_file}")
    print(f"  Output: {dist_dir}")

    os.chdir(project_root)
    result = os.system(f'pyinstaller "{spec_file}" --clean')

    if result != 0:
        print("\n❌ Build failed!")
        sys.exit(1)

    # Create artifacts directory in output
    artifacts_dir = dist_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    # Create README for the distribution
    readme = dist_dir / "README.txt"
    readme.write_text("""Enterprise Data Agent v2.0
========================

Quick Start:
1. Make sure PostgreSQL is running on localhost:5432
2. Create database 'eiw' with user 'eiw' / password 'eiw'
3. Double-click EnterpriseDataAgent.exe
4. Open http://localhost:8000 in your browser

Environment Variables (optional):
- EIW_DATABASE_URL: PostgreSQL connection string
- EIW_ARTIFACT_ROOT: Directory for analysis artifacts
- EIW_MODEL_PROVIDER: 'deterministic' (default) or 'anthropic'
- ANTHROPIC_API_KEY: Your Anthropic API key for real AI
- BUDGET_LIMIT_USD: Monthly budget limit

For Docker deployment, see docker-compose.yml
""")

    print(f"\n✅ Build complete!")
    print(f"\nOutput: {dist_dir}")
    print(f"Size: {get_size(dist_dir)}")


def get_size(path: Path) -> str:
    """Get human-readable size of directory."""
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    for unit in ["B", "KB", "MB", "GB"]:
        if total < 1024:
            return f"{total:.1f} {unit}"
        total /= 1024
    return f"{total:.1f} TB"


if __name__ == "__main__":
    main()
