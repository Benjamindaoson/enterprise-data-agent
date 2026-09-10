import { createContext, useContext, useState, useCallback, useRef, ReactNode } from "react";
import { Analysis, AnalysisStatus, FindingBlock, PhaseStatus } from "../types";
import {
  createInitialAnalyses, ANALYSIS_PHASES_TEMPLATE, DEFAULT_FINDINGS, DEFAULT_INSIGHTS,
} from "../data/mock";

function buildFollowUpFinding(id: string, question: string): FindingBlock[] {
  const q = question.toLowerCase();
  if (q.includes("供应商 a") || q.includes("供应商a")) {
    return [{ type: "text", id: `fu_${id}_t1`, content: "**供应商 A 深入分析**：供应商 A 7 月下降集中在 SKU #4521（威士忌系列）和 SKU #3890（葡萄酒系列），出货量分别环比减少 62% 和 44%。根据履约记录，主要原因为仓储周转延误（供应商 A 确认 2026-07-12 起暂停部分 SKU 发货）。建议联系供应商 A 确认 8 月恢复计划。", source: "供应商履约系统 · SKU 明细", sourceDetail: "数据范围：2026-07 SKU 级别发货明细\n分析指标：出货量、履约率\n已知限制：退货数据尚未与净销售额对齐" }];
  }
  if (q.includes("品类") || q.includes("饮料")) {
    return [{ type: "text", id: `fu_${id}_t1`, content: "**品类拆解**：7 月品类结构变化主要体现在烈酒大类（↓18%）、葡萄酒大类（↓22%）、饮料伴侣（↑6%）。其中威士忌分类降幅最大（-31%），主要受供应商 A 仓储影响；精酿啤酒保持小幅增长（+4%），是结构变化中的亮点。", source: "品类管理系统 · 2026-07", sourceDetail: "数据范围：品类级别 2026-06 至 2026-07\n分析维度：大类 / 小类\n已知限制：新品品类分类尚不完整" }, { type: "chart-breakdown", id: `fu_${id}_chart`, title: "品类变化贡献（%）", data: [{ factor: "烈酒", impact: -52, label: "-52%" }, { factor: "葡萄酒", impact: -31, label: "-31%" }, { factor: "饮料伴侣", impact: 9, label: "+9%" }, { factor: "精酿啤酒", impact: 4, label: "+4%" }], source: "品类管理系统 · 2026-07", sourceDetail: "计算说明：各品类变化量 / 总变化量 × 100%\n已知限制：精酿啤酒数据存在小额调整可能" }];
  }
  if (q.includes("数量") || q.includes("价格") || q.includes("结构")) {
    return [{ type: "text", id: `fu_${id}_t1`, content: "**数量变化细化**：数量下降（-68% 贡献）主要来自三个供应商的核心 SKU 断货，共涉及 23 个 SKU 停发。价格变化（-18% 贡献）与精品威士忌品类折扣促销有关。结构变化（-14% 贡献）体现在高价产品占比下降，消费者向中低价位产品转移。", source: "价格与结构分析模型", sourceDetail: "数据范围：SKU 级别 2026-06 至 2026-07\n分析方法：三因素拆解（数量效应 + 价格效应 + 结构效应）\n已知限制：新上线 SKU 暂未纳入结构分析" }];
  }
  if (q.includes("区域") || q.includes("地区") || q.includes("county") || q.includes("polk")) {
    return [{ type: "text", id: `fu_${id}_t1`, content: "**区域深入分析**：华东区（-12.3%）降幅最大，供应商 A 的仓储问题主要影响上海仓。华中区（-16.1%）降幅最严重，叠加结构性变化（高价产品流失）。西南区（+3.2%）是唯一正增长区域，成都门店新增高净值客户带动精品酒销售。Polk County 数据因区域数据延迟，目前无法给出精确结论。", source: "区域销售系统 · 2026-07", sourceDetail: "数据范围：大区 / 城市级别 2026-07\n已知限制：Polk County 数据存在 T+2 延迟，当前版本数据不完整" }];
  }
  if (q.includes("下一步") || q.includes("建议") || q.includes("措施")) {
    return [{ type: "text", id: `fu_${id}_t1`, content: "**下一步建议**：① **紧急**：联系供应商 A 确认 8 月恢复计划，重点 SKU 为 #4521 和 #3890；② **本周**：在供应商 A 缺货期间，协调供应商 D/E 扩大备货，填补烈酒品类缺口；③ **本月**：对华东区和华中区高风险门店启动应急补货方案；④ **下季度**：评估对供应商 A 的采购集中度，分散供应商风险。", source: "综合分析建议", sourceDetail: "建议基于：供应商贡献分析 + 区域风险评估 + 历史恢复周期数据\n已知限制：建议为 AI 生成，需与业务团队确认可行性" }];
  }
  return [{ type: "text", id: `fu_${id}_t1`, content: `**补充分析**：针对您的问题"${question}"，根据现有数据补充以下信息：当前数据集中，7 月相关维度的变化与供应商 A 的仓储异常高度相关。建议进一步确认该问题是否在 8 月已经改善，以判断是否为一次性冲击或持续性问题。如需更细粒度分析，请指定具体供应商、品类或区域维度。`, source: "综合分析", sourceDetail: "数据范围：2026-06 至 2026-07\n已知限制：当前仅有月度汇总数据，无周度明细" }];
}

interface AppContextValue {
  analyses: Analysis[];
  activeAnalysisId: string | null;
  createAnalysis: (question: string) => string;
  setActiveAnalysis: (id: string | null) => void;
  getAnalysis: (id: string) => Analysis | undefined;
  startAnalysisSimulation: (id: string) => void;
  appendFollowUp: (id: string, question: string) => void;
  updateAnalysisStatus: (id: string, status: AnalysisStatus) => void;
  cancelAnalysis: (id: string) => void;
  updateAnalysisQuestion: (id: string, question: string) => void;
  submitClarification: (id: string, answer: string) => void;
}

type AppCtx = ReturnType<typeof createContext<AppContextValue | null>>;
const _hmr = (import.meta as { hot?: { data: Record<string, unknown> } }).hot;
const AppContext: AppCtx = (_hmr?.data?.AppContext as AppCtx | undefined) ?? createContext<AppContextValue | null>(null);
if (_hmr) _hmr.data.AppContext = AppContext;

export function AppProvider({ children }: { children: ReactNode }) {
  const [analyses, setAnalyses] = useState<Analysis[]>(createInitialAnalyses());
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>[]>>(new Map());
  const clearTimersForId = (id: string) => { const timers = timersRef.current.get(id) ?? []; timers.forEach(clearTimeout); timersRef.current.delete(id); };
  const addTimer = (id: string, fn: () => void, ms: number) => { const t = setTimeout(fn, ms); const existing = timersRef.current.get(id) ?? []; timersRef.current.set(id, [...existing, t]); return t; };
  const updateAnalysis = useCallback((id: string, updater: (a: Analysis) => Analysis) => { setAnalyses(prev => prev.map(a => a.id === id ? updater(a) : a)); }, []);
  const getAnalysis = useCallback((id: string) => analyses.find(a => a.id === id), [analyses]);
  const createAnalysis = useCallback((question: string): string => {
    const id = `a${Date.now()}`;
    const newAnalysis: Analysis = { id, question, status: "preparing", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), phases: ANALYSIS_PHASES_TEMPLATE.map((label, i) => ({ id: `${id}_p${i}`, label, status: "waiting" as PhaseStatus })), currentPhaseIndex: -1, findings: [], insights: [], followUps: [] };
    setAnalyses(prev => [newAnalysis, ...prev]); return id;
  }, []);
  const startAnalysisSimulation = useCallback((id: string) => {
    clearTimersForId(id);
    updateAnalysis(id, a => ({ ...a, status: "running", findings: [], insights: [], currentPhaseIndex: 0 }));
    const phaseCount = ANALYSIS_PHASES_TEMPLATE.length;
    ANALYSIS_PHASES_TEMPLATE.forEach((_, i) => {
      addTimer(id, () => { setAnalyses(prev => prev.map(a => { if (a.id !== id || a.status === "cancelled") return a; return { ...a, status: "running", currentPhaseIndex: i, phases: a.phases.map((p, pi) => ({ ...p, status: pi < i ? "done" : pi === i ? "running" : "waiting" })) }; })); }, i * 950);
      addTimer(id, () => { setAnalyses(prev => prev.map(a => { if (a.id !== id || a.status === "cancelled") return a; return { ...a, phases: a.phases.map((p, pi) => ({ ...p, status: pi <= i ? "done" : "waiting" })) }; })); }, i * 950 + 700);
    });
    DEFAULT_FINDINGS.forEach((finding, fi) => addTimer(id, () => { setAnalyses(prev => prev.map(a => { if (a.id !== id || a.status === "cancelled") return a; return { ...a, findings: [...a.findings, finding], updatedAt: new Date().toISOString() }; })); }, Math.max(2000, fi * 900) + 400));
    DEFAULT_INSIGHTS.forEach((insight, ii) => addTimer(id, () => { setAnalyses(prev => prev.map(a => { if (a.id !== id || a.status === "cancelled") return a; return { ...a, insights: [...a.insights, insight] }; })); }, 3000 + ii * 700));
    const totalMs = phaseCount * 950 + DEFAULT_FINDINGS.length * 900 + 1200;
    addTimer(id, () => { setAnalyses(prev => prev.map(a => { if (a.id !== id || a.status === "cancelled") return a; return { ...a, status: "done", currentPhaseIndex: phaseCount - 1, updatedAt: new Date().toISOString(), summary: "下降主要由三家供应商贡献，数量变化是核心驱动因素", phases: a.phases.map(p => ({ ...p, status: "done" as PhaseStatus })) }; })); clearTimersForId(id); }, totalMs);
  }, [updateAnalysis]);
  const appendFollowUp = useCallback((id: string, question: string) => { const followUpFindings = buildFollowUpFinding(`${id}_${Date.now()}`, question); const entry = { question, findings: followUpFindings, timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) }; updateAnalysis(id, a => ({ ...a, followUps: [...a.followUps, entry], findings: [...a.findings, ...followUpFindings], updatedAt: new Date().toISOString() })); }, [updateAnalysis]);
  const updateAnalysisStatus = useCallback((id: string, status: AnalysisStatus) => { updateAnalysis(id, a => ({ ...a, status, updatedAt: new Date().toISOString() })); }, [updateAnalysis]);
  const cancelAnalysis = useCallback((id: string) => { clearTimersForId(id); updateAnalysis(id, a => ({ ...a, status: "cancelled", updatedAt: new Date().toISOString() })); }, [updateAnalysis]);
  const updateAnalysisQuestion = useCallback((id: string, question: string) => { updateAnalysis(id, a => ({ ...a, question, updatedAt: new Date().toISOString() })); }, [updateAnalysis]);
  const submitClarification = useCallback((id: string, answer: string) => { const clarifyFinding: FindingBlock = { type: "text", id: `${id}_clarify_${Date.now()}`, content: `**已收到澄清**：${answer}\n\nAI 将基于以上信息继续分析。`, source: "用户澄清" }; updateAnalysis(id, a => ({ ...a, status: "running", clarificationQuestion: undefined, findings: [...a.findings, clarifyFinding], updatedAt: new Date().toISOString() })); startAnalysisSimulation(id); }, [updateAnalysis, startAnalysisSimulation]);
  return <AppContext.Provider value={{ analyses, activeAnalysisId, createAnalysis, setActiveAnalysis: setActiveAnalysisId, getAnalysis, startAnalysisSimulation, appendFollowUp, updateAnalysisStatus, cancelAnalysis, updateAnalysisQuestion, submitClarification }}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
