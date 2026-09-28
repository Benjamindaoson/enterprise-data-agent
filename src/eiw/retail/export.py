"""Self-contained executive HTML report rendering for BA Agent artifacts."""

from __future__ import annotations

import json
from html import escape

from eiw.retail.models import RetailAnalysisResponse


def render_report_html(response: RetailAnalysisResponse) -> str:
    """Render a portable, print-friendly report without external dependencies."""

    def items(values: list[str]) -> str:
        return "".join(f"<li>{escape(str(value))}</li>" for value in values)

    driver_rows = "".join(
        (
            "<tr>"
            f"<td>{escape(str(row.get('title', '')))}</td>"
            f"<td>{escape(str(row.get('driver', '')))}</td>"
            f"<td>{escape(str(row.get('impact', '')))}</td>"
            f"<td>{float(row.get('score', 0.0)):.2f}</td>"
            "</tr>"
        )
        for row in response.report.key_drivers
    )
    action_rows = "".join(
        (
            "<article class='action'>"
            f"<span>{escape(action.priority)}</span>"
            "<div>"
            f"<h3>{escape(action.action)}</h3>"
            f"<p><b>Target:</b> {escape(action.target)}</p>"
            f"<p>{escape(action.rationale)}</p>"
            f"<small>Monitor: {escape(action.monitor_kpi)}</small>"
            "</div>"
            "</article>"
        )
        for action in response.report.actions
    )

    chart_blocks = "".join(
        f"<section class='chart-block'><div id='report-chart-{index}' class='chart'></div></section>"
        for index, _ in enumerate(response.charts)
    )
    chart_payload = json.dumps(
        [chart.option for chart in response.charts],
        ensure_ascii=False,
    ).replace("</", "<\\/")

    kpis = response.kpis
    sales = float(kpis.get("current_sales") or 0.0)
    sales_change = float(kpis.get("sales_change_pct") or 0.0)
    units = float(kpis.get("current_units") or 0.0)
    baskets = int(kpis.get("current_baskets") or 0)
    average_basket = float(kpis.get("avg_basket_value") or 0.0)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(response.report.title)}</title>
<style>
@page{{size:A4;margin:16mm}}
*{{box-sizing:border-box}}
body{{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#11222d;margin:0;background:#f4f1ea}}
main{{max-width:1080px;margin:32px auto;background:white;padding:42px 48px}}
.eyebrow{{font-size:11px;letter-spacing:.14em;color:#126e64;font-weight:800;text-transform:uppercase}}
h1,h2{{font-family:Georgia,serif;font-weight:500}}h1{{font-size:40px;margin:8px 0 10px}}h2{{font-size:26px;margin-top:34px}}
.meta{{color:#687983;font-size:12px}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #dfe5e8;margin:28px 0}}
.kpi{{padding:16px;border-right:1px solid #dfe5e8}}.kpi:last-child{{border-right:0}}.kpi span{{font-size:10px;text-transform:uppercase;color:#687983}}.kpi b{{display:block;font:24px Georgia,serif;margin-top:4px}}
ul{{padding-left:20px}}li{{margin:8px 0;line-height:1.5}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:10px;border-bottom:1px solid #e4e8ea;text-align:left;vertical-align:top}}th{{font-size:10px;text-transform:uppercase;color:#687983}}
.action{{display:grid;grid-template-columns:44px 1fr;border-top:1px solid #dfe5e8;padding:15px 0;gap:10px}}.action>span{{color:#b94b35;font-weight:800}}.action h3{{margin:0 0 6px;font-size:15px}}.action p{{margin:4px 0;font-size:12px;line-height:1.45}}.action small{{color:#687983}}
.chart-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.chart-block{{border:1px solid #dfe5e8;padding:12px;break-inside:avoid}}.chart{{height:320px}}
.footer{{margin-top:36px;padding-top:14px;border-top:1px solid #dfe5e8;color:#687983;font-size:10px}}
@media print{{body{{background:white}}main{{margin:0;max-width:none;padding:0}}}}
</style>
</head>
<body><main>
<div class="eyebrow">BA Agent · Retail Intelligence</div>
<h1>{escape(response.report.title)}</h1>
<div class="meta">Task {escape(response.task_id)} · dataset {escape(str(response.dataset.get("label", "")))} · weeks {escape(str(response.current_weeks))}</div>
<section class="kpis">
<div class="kpi"><span>Sales</span><b>${sales:,.0f}</b><small>{sales_change:+.1f}% vs prior</small></div>
<div class="kpi"><span>Units</span><b>{units:,.0f}</b></div>
<div class="kpi"><span>Baskets</span><b>{baskets:,}</b></div>
<div class="kpi"><span>Avg basket</span><b>${average_basket:,.2f}</b></div>
</section>
<h2>Executive summary</h2><ul>{items(response.report.executive_summary)}</ul>
<h2>Decision charts</h2><div class="chart-grid">{chart_blocks}</div>
<h2>Key business drivers</h2>
<table><thead><tr><th>Finding</th><th>Driver</th><th>Impact</th><th>Score</th></tr></thead><tbody>{driver_rows}</tbody></table>
<h2>Opportunities</h2><ul>{items(response.report.opportunities) if response.report.opportunities else "<li>No ranked opportunity met the current threshold.</li>"}</ul>
<h2>Priority actions</h2>{action_rows}
<h2>Monitoring</h2><ul>{items(response.report.monitoring)}</ul>
<div class="footer">Generated from typed analytical outputs. Merchandising associations are not presented as causal effects without matched or experimental evidence.</div>
</main>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<script>
const options={chart_payload};
options.forEach((option,index)=>{{
  const node=document.getElementById("report-chart-"+index);
  if(node){{const chart=echarts.init(node);chart.setOption(option);}}
}});
</script>
</body></html>"""
