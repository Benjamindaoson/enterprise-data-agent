from eiw.retail.data import RetailDataEngine
from eiw.retail.export import render_report_html
from eiw.retail.models import RetailAnalysisRequest
from eiw.retail.runtime import RetailBARuntime


def test_html_report_contains_decision_artifacts_and_escapes_input() -> None:
    response = RetailBARuntime(RetailDataEngine.demo()).analyze(
        RetailAnalysisRequest(question="<script>alert('x')</script> why did sales decline?")
    )
    rendered = render_report_html(response)

    assert "<script>alert" not in rendered
    assert "Executive summary" in rendered
    assert "Priority actions" in rendered
    assert response.task_id in rendered
