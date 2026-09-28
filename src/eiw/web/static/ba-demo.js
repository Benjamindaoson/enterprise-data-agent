const $ = (q) => document.querySelector(q);
const activity = $("#activity"), charts = $("#charts"), insightList = $("#insightList");
const runBtn = $("#runBtn"), question = $("#question"), report = $("#report");
let clock = null, startedAt = 0;

function addEvent(evt){
  const el=document.createElement("div"); el.className="event active";
  el.innerHTML=`<b>${evt.message}</b><small>${evt.workstream || evt.event_type}</small>`;
  activity.prepend(el);
  setTimeout(()=>el.classList.remove("active"),1300);
}

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
function renderInsights(items){
  $("#insightCount").textContent=items.length;
  insightList.innerHTML="";
  items.forEach((x,i)=>{
    setTimeout(()=>{
      const el=document.createElement("article"); el.className="insight-card";
      el.innerHTML=`<span class="score">Insight score ${Math.round(x.score*100)}</span><h3>${x.title}</h3><p>${x.finding}</p><button>继续调查</button>`;
      el.querySelector("button").onclick=()=>{question.value=`继续调查：${x.title}。重点解释驱动因素和下一步行动。`; question.focus();};
      insightList.appendChild(el);
    },i*90);
  });
}
function renderCharts(items){
  charts.innerHTML="";
  items.forEach((x,i)=>{
    const card=document.createElement("div"); card.className="chart-card";
    const id=`chart-${i}-${Date.now()}`; card.innerHTML=`<div id="${id}" class="chart"></div>`; charts.appendChild(card);
    const option=JSON.parse(JSON.stringify(x.option));
    option.color=["#126e64","#b94b35","#a57a25","#56758a"];
    option.textStyle={fontFamily:'Inter, sans-serif',color:"#0f1f2b"};
    const chart=echarts.init(document.getElementById(id)); chart.setOption(option);
    new ResizeObserver(()=>chart.resize()).observe(card);
    chart.on("click",(params)=>{question.value=`继续下钻 ${params.name}，解释它对经营表现的影响，并给出行动建议。`;});
  });
}
function renderReport(r){
  report.classList.remove("hidden");
  report.innerHTML=`<h2>${r.title}</h2>
  <h3>Executive summary</h3><ul>${r.executive_summary.map(x=>`<li>${x}</li>`).join("")}</ul>
  <h3>Priority actions</h3>
  ${r.actions.map(a=>`<div class="action"><b>${a.priority}</b><div><strong>${a.action}</strong><p>${a.rationale}</p><small>Monitor: ${a.monitor_kpi}</small></div></div>`).join("")}`;
}
function renderResult(r){
  renderKpis(r.kpis); renderInsights(r.insights); renderCharts(r.charts); renderReport(r.report);
  $("#hero").classList.remove("waiting");
  $("#hero").innerHTML=`<p>Executive finding</p><h2>${r.insights[0]?.title || "分析完成"}</h2>`;
}
async function loadStatus(){
  const r=await fetch("/api/v1/ba/retail/status"); const j=await r.json();
  $("#datasetStatus").textContent=`${j.dataset.label} · ${Number(j.dataset.counts.retail_transactions).toLocaleString()} rows`;
}
async function run(){
  runBtn.disabled=true; activity.innerHTML=""; charts.innerHTML=""; insightList.innerHTML=""; report.classList.add("hidden"); $("#kpis").innerHTML="";
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
        const msg=JSON.parse(line.slice(6)); if(msg.kind==="event") addEvent(msg.payload); if(msg.kind==="result") renderResult(msg.payload);
      }
    }
  }catch(err){addEvent({message:"分析失败："+err,event_type:"error"});}finally{clearInterval(clock);runBtn.disabled=false;}
}
runBtn.onclick=run; loadStatus().catch(()=>{$("#datasetStatus").textContent="Demo dataset"});
