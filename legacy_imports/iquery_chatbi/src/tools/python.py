"""
Python 执行工具

提供 Python 代码执行功能。
"""

from typing import Dict


class PythonTool:
    """
    Python 代码执行工具

    允许执行任意 Python 代码进行数据分析和可视化。
    """

    def __init__(self):
        self._schema = {
            "name": "python_inter",
            "description": "执行 Python 代码进行数据分析、统计计算和可视化图表生成。",
            "parameters": {
                "type": "object",
                "properties": {
                    "py_code": {
                        "type": "string",
                        "description": "要执行的 Python 代码，使用 pandas 进行数据分析，使用 matplotlib/seaborn 进行可视化"
                    }
                },
                "required": ["py_code"]
            }
        }

    def execute(self, py_code: str) -> str:
        py_code = self._preprocess_code(py_code)
        global_vars_before = set(globals().keys())
        try:
            exec(py_code, globals())
        except Exception as e:
            return f"执行错误: {str(e)}"
        global_vars_after = set(globals().keys())
        new_vars = global_vars_after - global_vars_before
        if new_vars:
            result = {}
            for var in new_vars:
                try:
                    val = globals()[var]
                    result[var] = repr(val)[:100]
                except:
                    pass
            return str(result)
        return "代码执行完成"

    def _preprocess_code(self, code: str) -> str:
        if "plt." in code or "sns." in code:
            if "fig" not in code and "plt.figure" not in code:
                plot_keywords = ["plt.", "sns.", "plt.show()"]
                for keyword in plot_keywords:
                    idx = code.find(keyword)
                    if idx != -1:
                        code = code[:idx] + "fig = plt.figure()\n" + code[idx:]
                        break
        return code

    def get_schema(self) -> Dict:
        return self._schema
