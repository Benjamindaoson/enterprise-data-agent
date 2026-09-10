"""Legacy iQuery ReAct planning engine. Preserved for design reference."""

import json
from typing import Any, Dict, List, Optional


class PlanningEngine:
    def __init__(self, available_functions: List[Dict], functions_dic: Dict[str, callable]):
        self.available_functions = available_functions
        self.functions_dic = functions_dic

    def should_act(self, response_message) -> bool:
        return hasattr(response_message, "tool_calls") and response_message.tool_calls is not None

    def get_function_calls(self, response_message) -> List[Dict[str, Any]]:
        if not self.should_act(response_message):
            return []
        return [
            {
                "id": tool_call.id,
                "name": tool_call.function.name,
                "arguments": json.loads(tool_call.function.arguments),
            }
            for tool_call in response_message.tool_calls
        ]

    def suggest_function(self, user_request: str) -> Optional[str]:
        user_lower = user_request.lower()
        keywords_map = [
            ("extract_data", ["提取", "保存", "dataframe", "到本地", "导出", "下载"]),
            ("python_inter", ["分析", "统计", "计算", "绘图", "可视化", "图表", "生成"]),
            ("sql_inter", ["sql", "查询", "数据库", "show", "select", "列出"]),
        ]
        for func_name, keywords in keywords_map:
            if any(kw in user_lower for kw in keywords):
                for available_func in self.functions_dic.keys():
                    if func_name in available_func or available_func in func_name:
                        return available_func
        return None

    def format_functions_description(self) -> str:
        if not self.available_functions:
            return "无可用工具"
        descriptions = []
        for func in self.available_functions:
            func_info = func.get("function", func)
            descriptions.append(f"- {func_info.get('name', 'unknown')}: {func_info.get('description', '无描述')}")
        return "\n".join(descriptions)
