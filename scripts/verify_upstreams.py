from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "third_party/deepanalyze": [
        "LICENSE",
        "deepanalyze.py",
        "scripts/single.sh",
        "scripts/multi_coldstart.sh",
        "scripts/multi_rl.sh",
    ],
    "third_party/data-formulator": [
        "LICENSE",
        "README.md",
        "py-src/data_formulator",
        "src/views/DataThread.tsx",
    ],
    "third_party/wrenai": [
        "LICENSE",
        "core",
        "sdk",
        "skills",
    ],
}

def main() -> int:
    missing: list[str] = []
    for base, rels in REQUIRED.items():
        base_path = ROOT / base
        if not base_path.exists():
            missing.append(f"{base} (submodule not initialized)")
            continue
        for rel in rels:
            path = base_path / rel
            if not path.exists():
                missing.append(str(path.relative_to(ROOT)))

    if missing:
        print("Upstream bootstrap verification FAILED:")
        for item in missing:
            print(f"  - {item}")
        print("\nRun: git submodule update --init --recursive")
        return 1

    print("Upstream bootstrap verification PASS")
    for base in REQUIRED:
        print(f"  - {base}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
