from datetime import datetime
from pathlib import Path

from agent.main_agent import main_agent


def normalize_text(text: str) -> str:
    return (
        text.replace(",", "")
        .replace("，", "")
        .replace(" ", "")
        .replace("\n", "")
        .replace("¥", "")
        .replace("元", "")
    )


def extract_answer(result) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""
    last_message = messages[-1]
    if hasattr(last_message, "content"):
        return last_message.content
    if isinstance(last_message, dict):
        return last_message.get("content", "")
    return str(last_message)


def check_keywords(answer: str, expected_keywords: list[str]) -> tuple[bool, list[str]]:
    normalized_answer = normalize_text(answer)
    missing = []
    for keyword in expected_keywords:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword not in normalized_answer:
            missing.append(keyword)
    return len(missing) == 0, missing


TEST_CASES = [
    {
        "id": 1,
        "name": "药品总库存、总销量、总销售额",
        "question": "查询每个药品的总库存、总销量和总销售额，并按总销售额从高到低排序。",
        "expected_keywords": ["连花清瘟", "60000", "11000", "348000", "布洛芬", "18000", "6000", "90000"],
    },
    {
        "id": 2,
        "name": "区域销售额排名",
        "question": "查询每个销售区域的总销售额，并按销售额从高到低排序。",
        "expected_keywords": ["华中区", "348000", "华东区", "90000", "华南区", "24500"],
    },
    {
        "id": 3,
        "name": "库存最高前三药品",
        "question": "查询库存最高的前三个药品。",
        "expected_keywords": ["连花清瘟", "60000", "布洛芬", "18000", "阿莫西林", "13000"],
    },
    {
        "id": 4,
        "name": "销售额最高前三药品",
        "question": "查询销售额最高的前三个药品。",
        "expected_keywords": ["连花清瘟", "348000", "布洛芬", "90000", "二甲双胍", "24500"],
    },
    {
        "id": 5,
        "name": "库存高但销量低风险分析",
        "question": "基于所有销售记录，计算每个药品的总库存、总销量、库存销量比=总库存/总销量，找出库存销量比最高的前三个药品，并分析库存风险。不要使用近6个月口径。",
        "expected_keywords": ["库存销量比", "立普妥", "22.00", "阿莫仙", "18.57", "格华止", "14.29"],
    },
]


def run_one_case(case: dict) -> dict:
    result = main_agent.invoke({"messages": [{"role": "user", "content": case["question"]}]})
    answer = extract_answer(result)
    passed, missing = check_keywords(answer, case["expected_keywords"])
    return {"id": case["id"], "name": case["name"], "question": case["question"], "answer": answer, "passed": passed, "missing": missing}


def save_report(results: list[dict]) -> Path:
    output_dir = Path("output") / "evals"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"db_agent_eval_{timestamp}.md"
    total = len(results)
    passed_count = sum(1 for item in results if item["passed"])
    lines = ["# 数据库 Agent 自动验收报告", "", f"- 测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"- 测试总数：{total}", f"- 通过数量：{passed_count}", f"- 通过率：{passed_count}/{total}", ""]
    for item in results:
        status = "通过" if item["passed"] else "未通过"
        lines += ["---", "", f"## 测试 {item['id']}：{item['name']}", "", f"**验收结果：{status}**", "", "### 用户问题", "", item["question"], ""]
        if item["missing"]:
            lines += ["### 缺失关键词", ""] + [f"- {m}" for m in item["missing"]] + [""]
        lines += ["### Agent 回答", "", item["answer"], ""]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main():
    results = []
    for case in TEST_CASES:
        try:
            results.append(run_one_case(case))
        except Exception as e:
            results.append({"id": case["id"], "name": case["name"], "question": case["question"], "answer": f"执行失败：{e}", "passed": False, "missing": case["expected_keywords"]})
    report_path = save_report(results)
    print(f"验收报告已生成：{report_path}")


if __name__ == "__main__":
    main()
