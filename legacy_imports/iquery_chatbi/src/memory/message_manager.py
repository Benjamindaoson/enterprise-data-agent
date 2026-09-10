"""
消息管理器

管理对话消息和 token 计数。
"""

import tiktoken
from typing import List, Dict, Any


class MessageManager:
    """
    消息管理器

    管理 Chat 模型的消息列表，支持 token 计数和自动裁剪。
    """

    def __init__(
        self,
        system_content_list: List[str] = None,
        question: str = "你好。",
        tokens_thr: int = None,
        project: Any = None,
    ):
        """
        初始化消息管理器

        Args:
            system_content_list: 系统消息内容列表
            question: 初始问题
            tokens_thr: Token 阈值
            project: 关联项目
        """
        self.system_content_list = system_content_list or []
        self.system_messages: List[Dict] = []
        self.history_messages: List[Dict] = []
        self.messages: List[Dict] = []
        self.num_of_system_messages = 0
        self.tokens_count = 0
        self.tokens_thr = tokens_thr
        self.project = project
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

        # 初始化
        self._init_messages(question)

    def _init_messages(self, question: str):
        """初始化消息"""
        if self.system_content_list:
            for content in self.system_content_list:
                self.system_messages.append({"role": "system", "content": content})

            self.num_of_system_messages = len(self.system_content_list)
            system_tokens = len(self.encoding.encode("\n".join(self.system_content_list)))

            if self.tokens_thr and system_tokens >= self.tokens_thr:
                print("系统消息超出 Token 限制")
                self.system_messages = []
                self.num_of_system_messages = 0
            else:
                self.tokens_count += system_tokens

        self.history_messages = [{"role": "user", "content": question}]
        self.tokens_count += len(self.encoding.encode(question))
        self.messages = self.system_messages + self.history_messages

        if self.tokens_thr and self.tokens_count >= self.tokens_thr:
            print("用户问题超出 Token 限制")
            self.history_messages = []
            self.messages = self.system_messages
            self.tokens_count = len(self.encoding.encode("\n".join(
                m["content"] for m in self.system_messages
            )))

    def messages_append(self, new_message: Any):
        """
        添加消息

        Args:
            new_message: 新消息（字典或 ChatCompletionMessage）
        """
        if isinstance(new_message, dict):
            self.messages.append(new_message)
            self.tokens_count += len(self.encoding.encode(str(new_message)))
        elif hasattr(new_message, 'content'):
            self.messages.append({
                "role": "assistant",
                "content": new_message.content,
                "tool_calls": getattr(new_message, 'tool_calls', None),
            })
            self.tokens_count += len(self.encoding.encode(str(new_message.content or "")))

        self.history_messages = self.messages[self.num_of_system_messages:]
        self._trim_messages()

    def _trim_messages(self):
        """裁剪消息以满足 Token 限制"""
        if self.tokens_thr is None:
            return

        while self.tokens_count >= self.tokens_thr and len(self.history_messages) > 1:
            removed = self.history_messages.pop(0)
            self.tokens_count -= len(self.encoding.encode(str(removed)))
            self.messages = self.system_messages + self.history_messages

    def messages_pop(self, manual: bool = False, index: int = None):
        """删除消息"""
        if manual and index is not None:
            if -len(self.history_messages) <= index < len(self.history_messages):
                removed = self.history_messages.pop(index if index >= 0 else len(self.history_messages) + index)
                self.tokens_count -= len(self.encoding.encode(str(removed)))
                self.messages = self.system_messages + self.history_messages

    def reset(self, question: str = "你好。"):
        """重置消息"""
        self._init_messages(question)

    def get_conversation_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.history_messages.copy()
