"""First-party bounded code-analysis worker for BA Agent AI Coding tasks."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from eiw.retail.data import RetailDataEngine


class GeneratedAnalysisCode(BaseModel):
    code: str = Field(min_length=1, max_length=20_000)
    explanation: str = Field(default="", max_length=1_000)


class CodeGenerationPolicy(Protocol):
    def generate(
        self,
        *,
        instruction: str,
        columns: list[str],
        sample_rows: list[dict[str, Any]],
    ) -> GeneratedAnalysisCode: ...


@dataclass
class OpenAICompatibleCodeGenerator:
    base_url: str
    model: str
    api_key: str = ""
    timeout_seconds: float = 90.0

    def generate(
        self,
        *,
        instruction: str,
        columns: list[str],
        sample_rows: list[dict[str, Any]],
    ) -> GeneratedAnalysisCode:
        prompt = {
            "instruction": instruction,
            "data_contract": {
                "path_variable": "data_path",
                "format": "CSV",
                "columns": columns,
                "sample_rows": sample_rows,
            },
            "execution_contract": {
                "allowed_packages": ["polars", "numpy", "csv", "statistics", "math"],
                "network": "disabled",
                "filesystem": "read-only except temporary runtime internals",
                "required_output": (
                    "assign a JSON-serializable dict/list/number/string to variable result"
                ),
            },
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Generate bounded data-analysis Python. Return only a JSON "
                            "object with code and explanation. Do not access network, "
                            "files other than data_path, environment variables, or OS APIs."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(prompt, ensure_ascii=False),
                    },
                ],
                "temperature": 0.0,
                "stream": False,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        raw = str(response.json()["choices"][0]["message"]["content"])
        return GeneratedAnalysisCode.model_validate(self._parse_json(raw))

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Code model did not return a JSON object")
        value = json.loads(raw[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("Generated code payload must be a JSON object")
        return value


@dataclass
class DockerCodeSandbox:
    image: str = "ba-agent-code-sandbox:local"
    timeout_seconds: float = 30.0
    memory_mb: int = 512
    cpus: float = 1.0
    pids_limit: int = 64
    repo_root: Path | None = None

    def available(self) -> bool:
        return shutil.which("docker") is not None

    def ensure_image(self) -> None:
        if not self.available():
            raise RuntimeError("Docker is required for first-party code analysis")
        inspected = subprocess.run(
            ["docker", "image", "inspect", self.image],
            capture_output=True,
            text=True,
            check=False,
        )
        if inspected.returncode == 0:
            return
        root = self.repo_root or Path(__file__).resolve().parents[3]
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(root / "docker" / "ba-code-sandbox.Dockerfile"),
                "-t",
                self.image,
                str(root),
            ],
            check=True,
            timeout=300,
        )

    def execute(self, code: str, *, input_csv: Path) -> dict[str, Any]:
        self.ensure_image()
        runner = self._runner(code)
        with tempfile.TemporaryDirectory(prefix="ba-code-sandbox-") as tmp:
            runner_path = Path(tmp) / "runner.py"
            runner_path.write_text(runner, encoding="utf-8")
            command = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--memory",
                f"{self.memory_mb}m",
                "--cpus",
                str(self.cpus),
                "--pids-limit",
                str(self.pids_limit),
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "-v",
                f"{runner_path.resolve()}:/workspace/runner.py:ro",
                "-v",
                f"{input_csv.resolve()}:/workspace/input.csv:ro",
                self.image,
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Code sandbox failed: {message[:2000]}")
        prefix = "__BA_RESULT__"
        for line in reversed(completed.stdout.splitlines()):
            if line.startswith(prefix):
                parsed = json.loads(line[len(prefix) :])
                return {
                    "result": parsed,
                    "stdout": "\n".join(
                        item
                        for item in completed.stdout.splitlines()
                        if not item.startswith(prefix)
                    ),
                }
        raise RuntimeError("Code sandbox did not produce the required result variable")

    @staticmethod
    def _runner(code: str) -> str:
        encoded = json.dumps(code)
        return (
            "import json\n"
            "data_path='/workspace/input.csv'\n"
            "result=None\n"
            f"code={encoded}\n"
            "scope={'data_path':data_path,'result':result}\n"
            "exec(compile(code,'<generated-analysis>','exec'),scope,scope)\n"
            "value=scope.get('result')\n"
            "if hasattr(value,'to_dicts'): value=value.to_dicts()\n"
            "elif hasattr(value,'tolist'): value=value.tolist()\n"
            "print('__BA_RESULT__'+json.dumps(value,default=str,ensure_ascii=False))\n"
        )


class FirstPartyRetailCodeAnalyst:
    """Generate and execute bounded analytical code over a small typed snapshot."""

    def __init__(
        self,
        data: RetailDataEngine,
        generator: CodeGenerationPolicy,
        sandbox: DockerCodeSandbox,
    ) -> None:
        self.data = data
        self.generator = generator
        self.sandbox = sandbox

    def analyze(
        self,
        instruction: str,
        *,
        current_weeks: list[int],
        previous_weeks: list[int],
        max_rows: int = 100,
    ) -> dict[str, Any]:
        rows = self.data.cross_dimension_scan(
            current_weeks,
            previous_weeks,
            limit=max_rows,
        )
        if not rows:
            return {
                "status": "NO_DATA",
                "instruction": instruction,
                "rows_sent": 0,
                "provider": "first-party-code-worker",
            }

        columns = list(rows[0])
        generated = self.generator.generate(
            instruction=instruction,
            columns=columns,
            sample_rows=rows[:5],
        )
        with tempfile.TemporaryDirectory(prefix="ba-code-input-") as tmp:
            input_path = Path(tmp) / "input.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
            execution = self.sandbox.execute(generated.code, input_csv=input_path)

        return {
            "status": "COMPLETED",
            "instruction": instruction,
            "provider": "first-party-code-worker",
            "rows_sent": len(rows),
            "code": generated.code,
            "explanation": generated.explanation,
            "result": execution["result"],
            "stdout": execution["stdout"],
            "sandbox": {
                "network": "none",
                "memory_mb": self.sandbox.memory_mb,
                "cpus": self.sandbox.cpus,
                "pids_limit": self.sandbox.pids_limit,
                "read_only_root": True,
            },
        }
