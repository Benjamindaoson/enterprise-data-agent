"""Install and build EXE for Enterprise Data Agent."""
import subprocess
import sys
import os
from pathlib import Path

def run_cmd(cmd, desc):
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def main():
    project_root = Path(__file__).parent.parent

    # 1. Check if PyInstaller is installed
    print("\n" + "="*60)
    print("  Step 1: Checking PyInstaller")
    print("="*60)
    result = subprocess.run(
        [sys.executable, "-c", "import PyInstaller; print(PyInstaller.__version__)"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"PyInstaller already installed: {result.stdout.strip()}")
    else:
        print("Installing PyInstaller...")
        if not run_cmd(f"{sys.executable} -m pip install pyinstaller", "Installing PyInstaller"):
            print("Failed to install PyInstaller!")
            return 1

    # 2. Ensure project dependencies
    print("\n" + "="*60)
    print("  Step 2: Installing project dependencies")
    print("="*60)
    os.chdir(project_root)
    run_cmd(f"{sys.executable} -m pip install -e .", "Installing project in editable mode")

    # 3. Clean old build artifacts
    print("\n" + "="*60)
    print("  Step 3: Cleaning old build artifacts")
    print("="*60)
    for path in [project_root / "build", project_root / "dist"]:
        if path.exists():
            import shutil
            shutil.rmtree(path)
            print(f"  Removed: {path}")

    # 4. Build EXE
    print("\n" + "="*60)
    print("  Step 4: Building EXE with PyInstaller")
    print("="*60)
    spec_file = project_root / "eiw.spec"
    cmd = f'"{sys.executable}" -m PyInstaller "{spec_file}" --clean'

    result = subprocess.run(cmd, shell=True, cwd=str(project_root))
    if result.returncode != 0:
        print("Build failed!")
        return 1

    # 5. Create artifacts directory and README
    print("\n" + "="*60)
    print("  Step 5: Creating distribution files")
    print("="*60)
    dist_dir = project_root / "dist" / "EnterpriseDataAgent"
    artifacts_dir = dist_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    print(f"  Created artifacts directory: {artifacts_dir}")

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
    print(f"  Created README: {readme}")

    # 6. Report size
    print("\n" + "="*60)
    print("  BUILD COMPLETE!")
    print("="*60)
    total = sum(f.stat().st_size for f in dist_dir.rglob("*") if f.is_file())
    for unit in ["B", "KB", "MB", "GB"]:
        if total < 1024:
            print(f"Output: {dist_dir}")
            print(f"Size: {total:.1f} {unit}")
            break
        total /= 1024

    return 0

if __name__ == "__main__":
    sys.exit(main())
