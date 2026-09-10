from __future__ import annotations

import json
from datetime import date, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from app.models import ProductReview, SkuProduct
from app.tools import business_trend_chart, high_acos_campaigns, refund_risks, summarize_business


def answer(message: str, db: Session) -> str:
    tool_result = route_tool(message, db)
    if tool_result.startswith("VISUAL_PAYLOAD:"):
        return "已生成经营趋势图。\n" + tool_result
    return polish_with_llm(message, tool_result) or tool_result


def stream_events(text: str):
    for chunk in split_text(text, 12):
        yield f"event:token\n{format_sse_data(chunk)}\n\n"
    yield "event:done\ndata:[DONE]\n\n"


def format_sse_data(value: str) -> str:
    return "\n".join(f"data:{line}" for line in value.splitlines())


def route_tool(message: str, db: Session) -> str:
    text = message.lower()
    if any(k in text for k in ["图", "趋势", "chart", "trend"]):
        return business_trend_chart(db, 6, title="近6个月净销售额与利润趋势")
    if any(k in text for k in ["退款", "退货", "refund"]):
        return refund_risks(db)
    if any(k in text for k in ["acos", "roas", "广告", "ad "]):
        return high_acos_campaigns(db)
    if any(k in text for k in ["评论", "低星", "review"]):
        return review_insight(db)
    if any(k in text for k in ["listing", "标题", "五点"]):
        return listing_draft(db, message)
    return summarize_business(db)


def polish_with_llm(question: str, tool_result: str) -> str | None:
    if not LLM_API_KEY:
        return None
    try:
        res = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": LLM_MODEL,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": "你是企业经营数据分析助手。只能基于工具结果回答，不要编造数字。"},
                    {"role": "user", "content": f"用户问题：{question}\n\n工具结果：\n{tool_result}\n\n请用中文先给结论，再给关键数字和建议。"},
                ],
            },
            timeout=45,
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def review_insight(db: Session) -> str:
    since = date.today() - timedelta(days=30)
    reviews = db.scalars(select(ProductReview).where(ProductReview.rating <= 3, ProductReview.review_date >= since)).all()
    if not reviews:
        return "最近 30 天没有低星评论。"
    themes = {
        "物流/时效": ["delay", "late", "shipping", "delivery"],
        "质量/做工": ["quality", "broken", "damaged", "cheap"],
        "尺寸/适配": ["size", "fit", "small", "large"],
        "说明/预期": ["description", "picture", "different", "misleading"],
    }
    lines = [f"低星评论分析：共 {len(reviews)} 条 3 星及以下评论。"]
    for name, words in themes.items():
        count = sum(any(w in r.content.lower() for w in words) for r in reviews)
        lines.append(f"- {name}：{count} 条")
    lines.append("建议：优先处理出现频次最高的主题，并回看对应 SKU 的 Listing 描述、包装和物流链路。")
    return "\n".join(lines)


def listing_draft(db: Session, message: str) -> str:
    sku = db.scalar(select(SkuProduct).where(SkuProduct.sku_code.ilike("%EB-US-1001%"))) or db.scalar(select(SkuProduct))
    if not sku:
        return "当前演示库没有可用于 Listing 优化的 SKU。"
    return f"""Listing 优化草案（{sku.sku_code}）
- 标题：{sku.title} for Cross-border Growth
- 五点描述：突出核心卖点；说明适用场景；降低退货疑虑；补充包装/尺寸信息；强调售后保障。
- 关键词：{sku.category}, {sku.target_marketplace}, best value
- FAQ 方向：围绕尺寸、兼容性、物流时效和售后问题补充说明。"""


def split_text(text: str, size: int):
    for i in range(0, len(text), size):
        yield text[i:i + size]
