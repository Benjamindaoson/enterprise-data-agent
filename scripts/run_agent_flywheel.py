"""Run trajectory collection, failure mining and SFT dataset export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.flywheel.manager import FlywheelManager
from eiw.flywheel.policies import ExpertPolicy, RandomPolicy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("artifacts/flywheel"))
    parser.add_argument("--episodes-per-scenario", type=int, default=10)
    parser.add_argument("--policy", choices=["expert", "random"], default="expert")
    args = parser.parse_args()

    policy = ExpertPolicy() if args.policy == "expert" else RandomPolicy(41)
    manager = FlywheelManager(args.root)
    manager.collect(policy, episodes_per_scenario=args.episodes_per_scenario)
    print(json.dumps(manager.build_report(policy), indent=2))


if __name__ == "__main__":
    main()
