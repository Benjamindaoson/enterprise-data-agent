"""
Agent 核心模块

包含 Agent 主类和 ReAct 循环逻辑。
"""

import logging
from typing import Optional, Dict, Any, Tuple

from openai import OpenAI

from src.config.settings import settings
from src.memory.message_manager import MessageManager
from src.tools.registry import ToolRegistry
from src.agent.executor import ActionExecutor
from src.agent.planner import PlanningEngine


logger = logging.getLogger(__name__)


class Agent:
    """
    iQuery 智能数据分析 Agent

    核心功能：
    - 自然语言理解
    - 函数调用
    - 多轮对话
    - 错误恢复
    """

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        tokens_threshold: Optional[int] = None,
    ):
        """
        初始化 Agent

        Args:
            system_prompt: 系统提示词
            tokens_threshold: Token 阈值
        """
        # 初始化 OpenAI 客户端
        self._init_client()

        # 初始化消息管理器
        self.message_manager = MessageManager(
            system_content_list=[system_prompt or settings.load_knowledge_base()],
            tokens_thr=tokens_threshold or settings.agent.tokens_threshold,
        )

        # 初始化工具注册器
        self.tool_registry = ToolRegistry()

        # 初始化执行器
        self.executor = ActionExecutor(
            available_functions=self.tool_registry.get_function_dict()
        )

        # 初始化规划引擎
        self.planner = PlanningEngine(
            available_functions=self.tool_registry.get_tools(),
            functions_dic=self.tool_registry.get_function_dict(),
        )

        # 当前分析阶段
        self.current_stage: Optional[str] = None

        logger.info("Agent 初始化完成")

    def _init_client(self):
        """初始化 OpenAI 客户端"""
        self.client = OpenAI(
            api_key=settings.api.api_key,
            base_url=settings.api.base_url,
        )
        self.model = settings.api.model

    def chat(self, user_input: str) -> str:
        """
        处理用户消息

        Args:
            user_input: 用户输入

        Returns:
            Agent 回复
        """
        # 添加用户消息
        self.message_manager.messages_append({"role": "user", "content": user_input})

        # ReAct 主循环
        response = self._react_loop()

        # 添加助手回复
        self.message_manager.messages_append({"role": "assistant", "content": response})

        return response

    def _react_loop(self) -> str:
        """
        ReAct 风格的主循环

        Returns:
            最终回复
        """
        max_iterations = settings.agent.max_iterations

        for iteration in range(max_iterations):
            # 调用 LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.message_manager.messages,
                tools=self.tool_registry.get_tools(),
                tool_choice="auto",
            )

            response_message = response.choices[0].message

            # 检查是否有函数调用
            if self.planner.should_act(response_message):
                # 添加 LLM 的函数调用消息
                self.message_manager.messages_append(response_message)

                # 执行函数调用
                tool_calls = self.planner.get_function_calls(response_message)

                for tool_call in tool_calls:
                    logger.info(f"执行函数: {tool_call['name']} | 参数: {tool_call['arguments']}")

                    # 执行函数（带错误恢复）
                    result, _ = self._execute_with_recovery(
                        tool_call["name"],
                        tool_call["arguments"]
                    )

                    logger.info(f"函数结果: {str(result)[:100]}...")

                    # 添加函数执行结果
                    self.message_manager.messages_append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": tool_call["name"],
                        "content": result,
                    })

                # 继续循环
                continue

            else:
                # 没有函数调用，返回回复
                return response_message.content or "抱歉，我没有理解您的问题。"

        return "已达到最大迭代次数，请重试。"

    def _execute_with_recovery(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """
        执行函数并处理错误恢复

        Args:
            function_name: 函数名
            arguments: 函数参数

        Returns:
            (result, needs_retry)
        """
        result = self.executor.execute(function_name, arguments)

        if result.startswith("执行错误:") or result.startswith(f"函数 {function_name} 不存在"):
            return self.executor.execute_with_retry(function_name, arguments, max_retries=2)

        return result, False

    def set_stage(self, stage: Optional[str]):
        """设置分析阶段"""
        self.current_stage = stage

    def get_context_info(self) -> Dict[str, Any]:
        """获取上下文信息"""
        return {
            "tokens": self.message_manager.tokens_count,
            "stage": self.current_stage,
            "dataframes": self.executor.get_dataframes_info(),
            "figures": self.executor.get_generated_figures_count(),
        }

    def reset(self):
        """重置 Agent 状态"""
        self.message_manager = MessageManager(
            system_content_list=[settings.load_knowledge_base()],
            tokens_thr=settings.agent.tokens_threshold,
        )
        self.executor.clear_history()
