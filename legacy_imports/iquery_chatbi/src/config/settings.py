"""
配置管理模块

集中管理所有配置，支持环境变量和配置文件。
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    user: str = "iquery_agent"
    password: str = "iquery_agent"
    database: str = "iquery"
    charset: str = "utf8"


@dataclass
class APIConfig:
    """API 配置"""
    api_key: str = ""
    base_url: str = "https://newone.nxykj.tech/v1"
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 2000
    temperature: float = 0.7


@dataclass
class AgentConfig:
    """Agent 配置"""
    tokens_threshold: int = 3000
    max_iterations: int = 10
    auto_save: bool = True
    system_prompt: str = """你是一名资深数据分析师，擅长挖掘数字规律并进行深度分析。

你有以下工具可以使用：
- sql_inter: 执行 SQL 查询
- extract_data: 提取数据到 DataFrame
- python_inter: 执行 Python 代码进行分析

请用中文回答。"""


@dataclass
class StorageConfig:
    """存储配置"""
    base_path: str = ""
    default_project: str = "数据分析项目"
    knowledge_base: dict = field(default_factory=dict)


@dataclass
class WebConfig:
    """Web 配置"""
    host: str = "127.0.0.1"
    port: int = 9999
    debug: bool = False


class Settings:
    """全局配置管理器"""

    _instance: Optional['Settings'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 项目根目录
        self.project_root = Path(__file__).resolve().parents[2]

        # 数据库配置
        self.database = DatabaseConfig()

        # API 配置
        self.api = APIConfig()
        self.api.api_key = os.getenv("OPENAI_API_KEY", self.api.api_key)

        # Agent 配置
        self.agent = AgentConfig()

        # 存储配置
        self.storage = StorageConfig()
        self._setup_storage_paths()

        # Web 配置
        self.web = WebConfig()

        self._initialized = True

    def _setup_storage_paths(self):
        """设置存储路径"""
        # 知识库路径
        knowledge_path = self.project_root / "data" / "knowledge"

        # 检查知识库文件是否存在
        dict_file = knowledge_path / "iquery数据字典.md"
        biz_file = knowledge_path / "本公司数据分析师业务介绍.md"

        self.storage.knowledge_base = {}

        if dict_file.exists():
            self.storage.knowledge_base["data_dictionary"] = str(dict_file)
        if biz_file.exists():
            self.storage.knowledge_base["business_knowledge"] = str(biz_file)

        # 文档输出路径
        self.storage.base_path = str(self.project_root / "docs")

    def load_knowledge_base(self) -> str:
        """加载知识库"""
        parts = []

        for key, path in self.storage.knowledge_base.items():
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    parts.append(f.read())

        return "\n\n".join(parts) if parts else self.agent.system_prompt

    @classmethod
    def get_instance(cls) -> 'Settings':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# 全局配置实例
settings = Settings.get_instance()
