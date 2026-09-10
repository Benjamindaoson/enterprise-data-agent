from pathlib import Path

import yaml


def _load_yaml(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_yaml_path = Path(__file__).parents[1] / "prompt" / "prompts.yaml"

_config = _load_yaml(_yaml_path)

main_agent_config = _config["main_agent"]
sub_agents_config = _config["sub_agents"]


if __name__ == "__main__":
    print("主 Agent 配置：")
    print(main_agent_config)

    print("\n子 Agent 配置：")
    print(sub_agents_config)