"""Retail BA Agent vertical.

The retail package is the first reference vertical for the Business Analysis Agent.
It keeps business semantics, analytical skills, autonomous investigation, insight
mining, visualization, report generation and evaluation behind first-party
interfaces so upstream bootstrap components can be replaced incrementally.
"""

from eiw.retail.models import RetailAnalysisRequest, RetailAnalysisResponse
from eiw.retail.runtime import RetailBARuntime

__all__ = ["RetailAnalysisRequest", "RetailAnalysisResponse", "RetailBARuntime"]
