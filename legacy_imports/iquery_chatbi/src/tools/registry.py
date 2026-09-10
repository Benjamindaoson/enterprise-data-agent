"""
工具注册器

管理所有可用工具及其 schema。
"""

from typing import List, Dict, Any

from src.tools.sql import SQLTool
from src.tools.python import PythonTool
from src.tools.data import DataTool


class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._schemas = []
        self._register_default_tools()

    def _register_default_tools(self):
        sql_tool = SQLTool()
        self.register("sql_inter", sql_tool.execute, sql_tool.get_schema())
        data_tool = DataTool()
        self.register("extract_data", data_tool.execute, data_tool.get_schema())
        python_tool = PythonTool()
        self.register("python_inter", python_tool.execute, python_tool.get_schema())

    def register(self, name: str, func: callable, schema: Dict[str, Any]):
        self._tools[name] = func
        self._schemas.append({"type": "function", "function": schema})

    def get_tools(self) -> List[Dict]:
        return self._schemas

    def get_function_dict(self) -> Dict[str, callable]:
        return self._tools.copy()

    def get_tool(self, name: str) -> callable:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())
