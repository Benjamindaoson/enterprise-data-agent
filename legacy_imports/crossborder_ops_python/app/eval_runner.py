from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent import route_tool
from app.seed import init_db, seed_demo_data


def run_eval_cases(path: str | Path) -> dict:
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    Session = sessionmaker(engine)
    db = Session()
    seed_demo_data(db)

    passed = failed = 0
    failures = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        answer = route_tool(case["question"], db)
        missing = [item for item in case.get("mustContain", []) if item not in answer]
        if missing:
            failed += 1
            failures.append({"line": line_no, "missing": missing})
        else:
            passed += 1
    return {"passed": passed, "failed": failed, "failures": failures}


def main() -> None:
    result = run_eval_cases(Path("eval/cases.jsonl"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result["failed"] else 0)


if __name__ == "__main__":
    main()
