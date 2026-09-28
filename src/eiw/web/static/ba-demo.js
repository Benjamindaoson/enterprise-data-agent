const $ = (q) => document.querySelector(q);
const activity = $("#activity"), charts = $("#charts"), insightList = $("#insightList");
const runBtn = $("#runBtn"), question = $("#question"), report = $("#report");
let clock = null, startedAt = 0, currentResult = null;

function addEvent(evt){
  const el=document.createElement("div"); el.className="event active";
  const timing=evt.elapsed_ms==null?"":` · ${(evt.elapsed_ms/1000).toFixed(2)}s`;
  el.innerHTML=`<b>${escapeHtml(evt.message)}</b><small>${escapeHtml(evt.workstream || evt.event_type)}${timing}</small>`;
  activity.prepend(el);
  setTimeout(()=>el.classList.remove("active"),1300);
}

function escapeHtml(value){return String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]))}
function money(v){return new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}).format(v||0)}
function pct(v){return `${Number(v||0).toFixed(1)}%`}
function renderKpis(k){
  $("#kpis").innerHTML=[
    ["Sales",money(k.current_sales),pct(k.sales_change_pct)],
    ["Units",Math.round(k.current_units||0).toLocaleString(),pct(k.units_change_pct)],
    ["Baskets",Math.round(k.current_baskets||0).toLocaleString(),pct(k.basket_change_pct)],
    ["Avg basket",money(k.avg_basket_value),`Discount ${pct((k.discount_rate||0)*100)}`]
  ].map(([a,b,c])=>`<div class="kpi"><span>${a}</span><strong>${b}</strong><em class="${String(c).startsWith("-")?"neg":"pos"}">${c}</em></div>`).join("");
}
function appendInsight(x){
  if(document.querySelector(`[data-insight-id="${CSS.escape(x.insight_id)}"]`)) return;
  const el=document.createElement("article"); el.className="insight-card"; el.dataset.insightId=x.insight_id;
  el.innerHTML=`<span class="score">Insight score ${Math.round(x.score*100)}</span><h3>${escapeHtml(x.title)}</h3><p>${escapeHtml(x.finding)}</p><button>继续调查</button>`;
  el.querySelector("button").onclick=()=>{question.value=`继续调查：${x.title}。重点解释驱动因素和下一步行动。`; question.focus();};
  insightList.appendChild(el);
  $("#insightCount").textContent=insightList.children.length;
}
function renderInsights(items){
  $("#insightCount").textContent=items.length;
  insightList.innerHTML="";
  items.forEach((x,i)=>setTimeout(()=>appendInsight(x),i*60));
}
function appendChart(input){
  if(document.querySelector(`[data-chart-id="${CSS.escape(input.chart_id)}"]`)) return;
  let x=input;
  const card=document.createElement("div"); card.className="chart-card"; card.dataset.chartId=x.chart_id;
  const id=`chart-${charts.children.length}-${Date.now()}`; card.innerHTML=`<div id="${id}" class="chart"></div><button class="chart-restyle">改图</button>`; charts.appendChild(card);
  const option=JSON.parse(JSON.stringify(x.option));
  option.color=["#126e64","#b94b35","#a57a25","#56758a"];
  option.textStyle={fontFamily:'Inter, sans-serif',color:"#0f1f2b"};
  const chart=echarts.init(document.getElementById(id)); chart.setOption(option);
  new ResizeObserver(()=>chart.resize()).observe(card);
  chart.on("click",(params)=>{question.value=`继续下钻 ${params.name}，解释它对经营表现的影响，并给出行动建议。`;});
  card.querySelector(".chart-restyle").onclick=async()=>{
    const instruction=prompt("怎么改这张图？例如：换成折线图 / 改成横向排名");
    if(!instruction) return;
    const res=await fetch("/api/v1/ba/retail/charts/restyle",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({chart:x,instruction})});
    if(!res.ok) return;
    const updated=await res.json(); x=updated; chart.setOption(updated.option,true);
  };
}
function renderCharts(items){charts.innerHTML="";items.forEach(appendChart)}
function renderReport(r){
  report.classList.remove("hidden");
  report.innerHTML=`<div class="report-toolbar"><button id="exportReport">导出管理层报告</button></div><h2>${escapeHtml(r.title)}</h2>
  <h3>Executive summary</h3><ul>${r.executive_summary.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>
  <h3>Priority actions</h3>
  ${r.actions.map(a=>`<div class="action"><b>${escapeHtml(a.priority)}</b><div><strong>${escapeHtml(a.action)}</strong><p>${escapeHtml(a.rationale)}</p><small>Monitor: ${escapeHtml(a.monitor_kpi)}</small></div></div>`).join("")}`;
  $("#exportReport").onclick=exportReport;
}
async function exportReport(){
  if(!currentResult) return;
  const res=await fetch("/api/v1/ba/retail/report/html",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(currentResult)});
  if(!res.ok){addEvent({message:"报告导出失败",event_type:"error"});return;}
  const html=await res.text(), blob=new Blob([html],{type:"text/html"}), url=URL.createObjectURL(blob);
  const a=document.createElement("a"); a.href=url; a.download=`BA-Agent-${currentResult.task_id}.html`; a.click(); URL.revokeObjectURL(url);
}
function renderResult(r){
  currentResult=r;
  renderKpis(r.kpis);
  if(insightList.children.length===0) renderInsights(r.insights); else $("#insightCount").textContent=r.insights.length;
  if(charts.children.length===0) renderCharts(r.charts);
  renderReport(r.report);
  $("#hero").classList.remove("waiting");
  $("#hero").innerHTML=`<p>Executive finding</p><h2>${r.insights[0]?.title || "分析完成"}</h2>`;
}
async function loadStatus(){
  const r=await fetch("/api/v1/ba/retail/status"); const j=await r.json();
  const source=j.dataset.source||{};
  const provenance=source.license
    ? ` · ${source.license}${source.source_commit ? " · "+source.source_commit.slice(0,7) : ""}`
    : "";
  $("#datasetStatus").textContent=
    `${j.dataset.label} · ${Number(j.dataset.counts.retail_transactions).toLocaleString()} transactions${provenance}`;
}
async function run(){
  runBtn.disabled=true; currentResult=null; activity.innerHTML=""; charts.innerHTML=""; insightList.innerHTML=""; report.classList.add("hidden"); $("#kpis").innerHTML="";
  $("#hero").className="hero-card"; $("#hero").innerHTML="<p>Investigation running</p><h2>多个分析工作流正在并行扫描经营数据…</h2>";
  startedAt=performance.now(); clock=setInterval(()=>{$("#elapsed").textContent=((performance.now()-startedAt)/1000).toFixed(1)+"s"},100);
  try{
    const res=await fetch("/api/v1/ba/retail/analyze/stream",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:question.value})});
    const reader=res.body.getReader(), decoder=new TextDecoder(); let buffer="";
    while(true){
      const {value,done}=await reader.read(); if(done) break; buffer+=decoder.decode(value,{stream:true});
      const frames=buffer.split("\n\n"); buffer=frames.pop();
      for(const frame of frames){
        const line=frame.split("\n").find(x=>x.startsWith("data: ")); if(!line) continue;
        const msg=JSON.parse(line.slice(6));
        if(msg.kind==="event"){
          addEvent(msg.payload);
          if(msg.payload.event_type==="workstream_completed" && msg.payload.workstream==="overview" && msg.payload.payload?.metrics) renderKpis(msg.payload.payload.metrics);
          if(msg.payload.event_type==="insight_discovered") appendInsight(msg.payload.payload);
          if(msg.payload.event_type==="chart_ready") appendChart(msg.payload.payload);
        }
        if(msg.kind==="result") renderResult(msg.payload);
      }
    }
  }catch(err){addEvent({message:"分析失败："+err,event_type:"error"});}finally{clearInterval(clock);runBtn.disabled=false;}
}
runBtn.onclick=run; loadStatus().catch(()=>{$("#datasetStatus").textContent="Demo dataset"});
