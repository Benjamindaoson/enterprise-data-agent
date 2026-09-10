"""
iQuery - 智能数据分析平台
"""

__version__ = "1.0.0"
__author__ = "iQuery Team"

from src.agent.core import Agent
from src.config.settings import Settings

__all__ = ["Agent", "Settings"]
