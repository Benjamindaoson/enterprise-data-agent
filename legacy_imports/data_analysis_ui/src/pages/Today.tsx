import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useApp } from "../store/AppContext";
import { PRESET_QUESTIONS } from "../data/mock";
import { Analysis } from "../types";

function formatTime(isoString: string): string {
  const d = new Date(isoString);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const timeStr = d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  return isToday ? `今天 ${timeStr}` : `昨天 ${timeStr}`;
}

function toSessionTitle(question: string): string {
  const q = question.toLowerCase();
  if (q.includes("供应商") && (q.includes("贡献") || q.includes("来源") || q.includes("主要"))) return "供应商贡献分析";
  if (q.includes("供应商 a") || q.includes("供应商a")) return "供应商 A 深入分析";
  if (q.includes("品类") && q.includes("变化")) return "品类结构变化分析";
  if (q.includes("数量") && q.includes("价格")) return "数量价格结构拆解";
  if (q.includes("区域") || q.includes("county") || q.includes("polk")) return "区域表现分析";
  if (q.includes("7 月") || q.includes("7月")) return q.includes("变化") || q.includes("下降") || q.includes("为什么") ? "7月批发销售额变化分析" : "7月销售额分析";
  if (q.includes("销售额")) return "销售额变化分析";
  if (q.includes("趋势")) return "销售趋势分析";
  return question.length > 20 ? question.slice(0, 18) + "…" : question;
}

function statusMeta(a: Analysis): { label: string; color: string; dot?: string; action: string } {
  const map: Record<string, { label: string; color: string; dot?: string; action: string }> = {
    preparing: { label: "准备中", color: "text-[#9ca3af]", action: "查看进度" },
    running: { label: "分析中", color: "text-[#00897b]", dot: "bg-[#00897b]", action: "查看进度" },
    clarifying: { label: "需要澄清", color: "text-[#d97706]", dot: "bg-[#d97706]", action: "回答问题" },
    partial: { label: "部分完成", color: "text-[#6b7280]", action: "继续分析" },
    done: { label: "已完成", color: "text-[#9ca3af]", action: "继续分析" },
    failed: { label: "失败", color: "text-[#ef4444]", action: "重新分析" },
    cancelled: { label: "已取消", color: "text-[#9ca3af]", action: "重新分析" },
    insufficient: { label: "依据不足", color: "text-[#d97706]", dot: "bg-[#d97706]", action: "查看详情" },
  };
  return map[a.status] ?? map.done;
}

const TIME_RANGES = ["最近 1 个月（2026-07）", "最近 3 个月（2026-05 至 2026-07）", "最近 6 个月（2026-02 至 2026-07）", "本年至今（2026-01 至 2026-07）", "自定义时间范围"];
const COMPARE_BASES = ["与上月对比（环比）", "与去年同期对比（同比）", "与目标值对比", "与行业基准对比", "不设比较基准"];
const DIMENSIONS = [{ key: "supplier", label: "供应商" }, { key: "category", label: "品类" }, { key: "region", label: "区域" }, { key: "sku", label: "SKU" }, { key: "county", label: "县区" }, { key: "store", label: "门店" }];
const METRICS_QUICK = [{ key: "sales", label: "批发销售额" }, { key: "bottles", label: "售出瓶数" }, { key: "volume", label: "销售升数" }, { key: "avgprice", label: "平均批发价格" }];

function ScopeSetup({ question, onConfirm, onCancel }: { question: string; onConfirm: (q: string) => void; onCancel: () => void }) {
  const [q, setQ] = useState(question);
  const [timeRange, setTimeRange] = useState(TIME_RANGES[0]);
  const [compareBase, setCompareBase] = useState(COMPARE_BASES[0]);
  const [selectedDims, setSelectedDims] = useState<string[]>(["supplier", "category", "region"]);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(["sales", "bottles"]);
  const toggleDim = (key: string) => setSelectedDims(prev => prev.includes(key) ? prev.filter(d => d !== key) : [...prev, key]);
  const toggleMetric = (key: string) => setSelectedMetrics(prev => prev.includes(key) ? prev.filter(m => m !== key) : [...prev, key]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
      <div className="bg-white rounded-2xl border border-[#e4e7ec] shadow-xl w-full max-w-xl mx-4 overflow-hidden">
        <div className="px-6 py-5 border-b border-[#e4e7ec] flex items-center justify-between">
          <div><h2 className="text-[16px] font-semibold text-[#111827]">确认分析范围</h2><p className="text-[13px] text-[#6b7280] mt-0.5">确认后 AI 将开始分析，过程中也可以随时调整</p></div>
          <button onClick={onCancel} className="text-[#9ca3af] text-xl">×</button>
        </div>
        <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
          <div><label className="text-[12px] font-semibold text-[#374151] block mb-2">业务问题</label><textarea value={q} onChange={e => setQ(e.target.value)} rows={2} className="w-full px-3 py-2.5 text-[14px] border border-[#e4e7ec] rounded-lg outline-none resize-none" /></div>
          <div><label className="text-[12px] font-semibold text-[#374151] block mb-2">时间范围</label><div className="flex flex-wrap gap-2">{TIME_RANGES.map(r => <button key={r} onClick={() => setTimeRange(r)} className={`px-3 py-1.5 text-[12px] rounded-lg border ${timeRange === r ? "border-[#00897b] bg-[#e0f2f1] text-[#00897b]" : "border-[#e4e7ec]"}`}>{r}</button>)}</div></div>
          <div><label className="text-[12px] font-semibold text-[#374151] block mb-2">比较基准</label><div className="flex flex-wrap gap-2">{COMPARE_BASES.map(b => <button key={b} onClick={() => setCompareBase(b)} className={`px-3 py-1.5 text-[12px] rounded-lg border ${compareBase === b ? "border-[#00897b] bg-[#e0f2f1] text-[#00897b]" : "border-[#e4e7ec]"}`}>{b}</button>)}</div></div>
          <div><label className="text-[12px] font-semibold text-[#374151] block mb-2">分析维度</label><div className="flex flex-wrap gap-2">{DIMENSIONS.map(d => <button key={d.key} onClick={() => toggleDim(d.key)} className={`px-3 py-1.5 text-[12px] rounded-lg border ${selectedDims.includes(d.key) ? "border-[#00897b] bg-[#e0f2f1] text-[#00897b]" : "border-[#e4e7ec]"}`}>{d.label}</button>)}</div></div>
          <div><label className="text-[12px] font-semibold text-[#374151] block mb-2">分析指标</label><div className="flex flex-wrap gap-2">{METRICS_QUICK.map(m => <button key={m.key} onClick={() => toggleMetric(m.key)} className={`px-3 py-1.5 text-[12px] rounded-lg border ${selectedMetrics.includes(m.key) ? "border-[#00897b] bg-[#e0f2f1] text-[#00897b]" : "border-[#e4e7ec]"}`}>{m.label}</button>)}</div></div>
        </div>
        <div className="px-6 py-4 border-t border-[#e4e7ec] flex justify-between"><button onClick={onCancel}>返回修改问题</button><button onClick={() => onConfirm(q.trim() || question)} disabled={!q.trim()} className="px-6 py-2 bg-[#00897b] text-white rounded-lg">确认开始分析</button></div>
      </div>
    </div>
  );
}

export function Today() {
  const [input, setInput] = useState("");
  const [scopeQuestion, setScopeQuestion] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [analysisMode, setAnalysisMode] = useState<"auto" | "deep" | "quick">("auto");
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { analyses, createAnalysis, startAnalysisSimulation } = useApp();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const field = searchParams.get("field");
    const label = searchParams.get("label");
    if (field) {
      setInput(label ? `分析 ${label}（${field}）的分布和趋势` : `分析 ${field} 字段的数据分布`);
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  }, [searchParams]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  useEffect(() => {
    if (!settingsOpen) return;
    const handler = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) setSettingsOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [settingsOpen]);

  const handleRequestStart = (q?: string) => {
    const question = (q ?? input).trim();
    if (question) setScopeQuestion(question);
  };
  const handleConfirmStart = (q: string) => {
    setScopeQuestion(null);
    const id = createAnalysis(q);
    startAnalysisSimulation(id);
    navigate(`/analyses/${id}`);
  };
  const handlePresetClick = (q: string) => {
    const id = createAnalysis(q);
    startAnalysisSimulation(id);
    navigate(`/analyses/${id}`);
  };
  const MODE_LABELS: Record<string, string> = { auto: "自动", deep: "深度分析", quick: "快速查询" };

  return (
    <div className="flex-1 overflow-y-auto bg-white flex flex-col">
      {scopeQuestion !== null && <ScopeSetup question={scopeQuestion} onConfirm={handleConfirmStart} onCancel={() => setScopeQuestion(null)} />}
      <div className="flex-1 flex flex-col items-center px-8 pt-[8vh] pb-12">
        <div className="w-full max-w-[640px] flex flex-col gap-6">
          <div className="text-center"><h1 className="text-[26px] font-semibold text-[#111827]">今天想分析什么？</h1><p className="text-[13px] text-[#b0b8c4] mt-1.5">提出一个业务问题，AI 会自动分析数据、寻找原因，并生成可持续探索的分析结果。</p></div>
          <div className="bg-white border border-[#dde1e7] rounded-2xl shadow-[0_2px_20px_rgba(0,0,0,0.07)]">
            <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[#f0f2f5]"><span className="text-[12px] text-[#6b7280]">Iowa 酒类批发数据 · 截至 2026年7月</span><div className="flex-1" /><div className="relative" ref={settingsRef}><button onClick={() => setSettingsOpen(v => !v)} className="text-[11px] text-[#9ca3af]">分析设置</button>{settingsOpen && <div className="absolute right-0 top-full mt-2 w-56 bg-white border rounded-xl shadow-lg z-20 p-3">{(["auto", "deep", "quick"] as const).map(m => <button key={m} onClick={() => { setAnalysisMode(m); setSettingsOpen(false); }} className={`w-full px-3 py-2 rounded-lg text-left ${analysisMode === m ? "bg-[#e0f2f1] text-[#00897b]" : ""}`}>{MODE_LABELS[m]}</button>)}</div>}</div></div>
            <div className="flex items-start gap-3 px-4 py-3.5"><textarea ref={textareaRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleRequestStart(); } }} placeholder="提出一个关于业务数据的问题…" rows={1} className="flex-1 text-[15px] resize-none outline-none bg-transparent" /><button onClick={() => handleRequestStart()} disabled={!input.trim()} className="w-9 h-9 rounded-full bg-[#00897b] text-white disabled:opacity-25">↑</button></div>
          </div>
          <div><p className="text-[11px] font-semibold text-[#c0c4cc] uppercase tracking-widest mb-2">试试这些问题</p>{PRESET_QUESTIONS.map(q => <button key={q} onClick={() => handlePresetClick(q)} className="w-full text-left flex gap-2 py-1.5"><span>→</span><span className="text-[13px] text-[#9ca3af]">{q}</span></button>)}</div>
          <div><div className="flex justify-between mb-2"><p className="text-[11px] font-semibold text-[#c0c4cc] uppercase tracking-widest">最近分析</p><button onClick={() => navigate("/analyses")} className="text-[11px] text-[#c0c4cc]">查看全部分析</button></div>{analyses.slice(0, 2).map(item => { const meta = statusMeta(item); return <button key={item.id} onClick={() => navigate(`/analyses/${item.id}`)} className="w-full text-left py-2 flex justify-between"><div className="flex gap-2.5 min-w-0"><span className={`text-[13px] truncate ${meta.color}`}>{toSessionTitle(item.question)}</span><span className="text-[11px] text-[#9ca3af]">{meta.label} · {formatTime(item.updatedAt)}</span></div><span className="text-[11px] text-[#9ca3af]">继续分析</span></button>; })}</div>
        </div>
      </div>
    </div>
  );
}
