const $ = (q) => document.querySelector(q);
const activity = $("#activity"), charts = $("#charts"), insightList = $("#insightList");
const runBtn = $("#runBtn"), question = $("#question"), report = $("#report");
let clock = null, startedAt = 0, currentResult = null;
let pendingParentTaskId = null, pendingFocus = {};
const WORKSTREAMS=["overview","store","product","promotion","customer"];

function setWorkstreamState(name,state,message=""){
  const node=document.querySelector(`[data-workstream="${CSS.escape(name)}"]`);
  if(!node) return;
  node.classList.remove("running","done","failed");
  if(state!=="idle" && state!=="ready") node.classList.add(state);
  const badge=node.querySelector("em");
  if(badge) badge.textContent=state;
  if(message){
    const small=node.querySelector("small");
    if(small) small.title=message;
  }
}
function resetWorkstreams(){
  setWorkstreamState("supervisor","ready");
  WORKSTREAMS.forEach(name=>setWorkstreamState(name,"idle"));
}
function addEvent(evt){
  if(evt.event_type==="plan_ready" || evt.event_type==="replan_started") setWorkstreamState("supervisor","running",evt.message);
  if(evt.event_type==="replan_ready" || evt.event_type==="replan_skipped" || evt.event_type==="report_ready") setWorkstreamState("supervisor","done",evt.message);
  if(evt.event_type==="workstream_started" && evt.workstream) setWorkstreamState(evt.workstream,"running",evt.message);
  if(evt.event_type==="workstream_completed" && evt.workstream) setWorkstreamState(evt.workstream,"done",evt.message);
  if(evt.event_type==="workstream_failed" && evt.workstream) setWorkstreamState(evt.workstream,"failed",evt.message);
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
  el.querySelector("button").onclick=()=>{
    pendingParentTaskId=currentResult?.task_id||null;
    pendingFocus={...(x.dimensions||{})};
    question.value=`继续调查：${x.title}。重点解释驱动因素、影响范围和下一步行动。`;
    run();
  };
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
  chart.on("click",(params)=>{
    const linked=(x.insight_ids||[])
      .map(id=>(currentResult?.insights||[]).find(item=>item.insight_id===id))
      .find(Boolean);
    pendingParentTaskId=currentResult?.task_id||null;
    pendingFocus={...(linked?.dimensions||{})};
    if(!Object.keys(pendingFocus).length && params.name){
      pendingFocus={commodity:String(params.name)};
    }
    question.value=`继续下钻 ${params.name}，解释这个切片的主要驱动因素，并给出下一步行动。`;
    run();
  });
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
  report.innerHTML=`<div class="report-toolbar"><button id="exportReport">导出 HTML</button><button id="exportPdf">导出 PDF</button></div><h2>${escapeHtml(r.title)}</h2>
  <h3>Executive summary</h3><ul>${r.executive_summary.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>
  <h3>Priority actions</h3>
  ${r.actions.map(a=>`<div class="action"><b>${escapeHtml(a.priority)}</b><div><strong>${escapeHtml(a.action)}</strong><p>${escapeHtml(a.rationale)}</p><small>Monitor: ${escapeHtml(a.monitor_kpi)}</small></div></div>`).join("")}`;
  $("#exportReport").onclick=exportReport;
  $("#exportPdf").onclick=exportPdf;
}
async function exportReport(){
  if(!currentResult) return;
  const res=await fetch("/api/v1/ba/retail/report/html",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(currentResult)});
  if(!res.ok){addEvent({message:"报告导出失败",event_type:"error"});return;}
  const html=await res.text(), blob=new Blob([html],{type:"text/html"}), url=URL.createObjectURL(blob);
  const a=document.createElement("a"); a.href=url; a.download=`BA-Agent-${currentResult.task_id}.html`; a.click(); URL.revokeObjectURL(url);
}
async function exportPdf(){
  if(!currentResult) return;
  const res=await fetch("/api/v1/ba/retail/report/pdf",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(currentResult)});
  if(!res.ok){addEvent({message:"PDF 导出不可用，请安装 Playwright reporting dependency",event_type:"error"});return;}
  const blob=await res.blob(), url=URL.createObjectURL(blob);
  const a=document.createElement("a"); a.href=url; a.download=`BA-Agent-${currentResult.task_id}.pdf`; a.click(); URL.revokeObjectURL(url);
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
  runBtn.disabled=true; runBtn.textContent="自主分析中…"; currentResult=null; activity.innerHTML=""; charts.innerHTML=""; insightList.innerHTML=""; report.classList.add("hidden"); $("#kpis").innerHTML=""; resetWorkstreams();
  $("#hero").className="hero-card"; $("#hero").innerHTML="<p>Investigation running</p><h2>多个分析工作流正在并行扫描经营数据…</h2>";
  startedAt=performance.now(); clock=setInterval(()=>{$("#elapsed").textContent=((performance.now()-startedAt)/1000).toFixed(1)+"s"},100);
  try{
    const requestBody={
      question:question.value,
      parent_task_id:pendingParentTaskId,
      focus:pendingFocus
    };
    const res=await fetch("/api/v1/ba/retail/analyze/stream",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(requestBody)});
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
        if(msg.kind==="result"){
          renderResult(msg.payload);
          pendingParentTaskId=msg.payload.task_id;
          pendingFocus={};
        }
      }
    }
  }catch(err){
    addEvent({message:"分析失败："+err,event_type:"error"});
    setWorkstreamState("supervisor","failed",String(err));
  }finally{
    clearInterval(clock);runBtn.disabled=false;runBtn.textContent="开始自主分析";
  }
}
document.querySelectorAll(".prompt-presets button").forEach(btn=>{
  btn.addEventListener("click",()=>{
    question.value=btn.dataset.prompt||"";
    document.querySelectorAll(".prompt-presets button").forEach(x=>x.classList.remove("active"));
    btn.classList.add("active");
    question.focus();
  });
});
resetWorkstreams();
runBtn.onclick=run; loadStatus().catch(()=>{$("#datasetStatus").textContent="Demo dataset"});
