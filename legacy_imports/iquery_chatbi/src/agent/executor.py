"""Legacy iQuery action executor. Preserved for retry/history/chart-tracking ideas."""

import json
from typing import Any, Dict, Tuple

import matplotlib.pyplot as plt


class ActionExecutor:
    def __init__(self, available_functions: Dict[str, callable]):
        self.available_functions = available_functions
        self.execution_history = []
        self.context = {}
        self.generated_figures = []

    def execute(self, function_name: str, arguments: Dict[str, Any]) -> str:
        if function_name not in self.available_functions:
            error_msg = f"函数 {function_name} 不存在，可用函数: {list(self.available_functions.keys())}"
            self._record_execution(function_name, arguments, error_msg, success=False)
            return error_msg
        try:
            func = self.available_functions[function_name]
            py_code = arguments.get("py_code", "")
            has_plot = self._detect_plotting_code(py_code)
            figures_before = len(plt.get_fignums())
            result = func(**arguments)
            figures_after = plt.get_fignums()
            if has_plot and len(figures_after) > figures_before:
                for fig_num in figures_after[figures_before:]:
                    self.generated_figures.append(plt.figure(fig_num))
            self._record_execution(function_name, arguments, result, success=True)
            if result is not None:
                self.context[function_name] = result
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except Exception as e:
            error_msg = f"执行错误: {str(e)}"
            self._record_execution(function_name, arguments, error_msg, success=False)
            return error_msg

    def _detect_plotting_code(self, code: str) -> bool:
        if not code:
            return False
        keywords = ["plt.", "sns.", "plot(", "bar(", "hist(", "scatter(", "pie(", "heatmap("]
        return any(kw in code for kw in keywords)

    def execute_with_retry(self, function_name: str, arguments: Dict[str, Any], max_retries: int = 3) -> Tuple[str, bool]:
        result = ""
        for _ in range(max_retries):
            result = self.execute(function_name, arguments)
            if not result.startswith("执行错误:") and not result.startswith(f"函数 {function_name} 不存在"):
                return result, False
        return result, True

    def _record_execution(self, function_name: str, arguments: Dict, result: Any, success: bool):
        self.execution_history.append({
            "function": function_name,
            "arguments": arguments,
            "result": str(result)[:500] if result else "",
            "success": success,
        })

    def get_generated_figures_count(self) -> int:
        return len(self.generated_figures)

    def clear_history(self):
        self.execution_history = []
        self.context = {}
        self.generated_figures = []
        plt.close("all")
