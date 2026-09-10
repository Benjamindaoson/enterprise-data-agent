import { Analysis, FindingBlock, PhaseStatus } from "../types";

export const TREND_DATA = [
  { month: "2月", sales: 3820, prev: 3950 },
  { month: "3月", sales: 4210, prev: 4080 },
  { month: "4月", sales: 4590, prev: 4300 },
  { month: "5月", sales: 4380, prev: 4500 },
  { month: "6月", sales: 5120, prev: 4750 },
  { month: "7月", sales: 4340, prev: 5120 },
];

export const SUPPLIER_DATA = [
  { name: "供应商 A", contrib: -41, abs: 321 },
  { name: "供应商 B", contrib: -28, abs: 218 },
  { name: "供应商 C", contrib: -19, abs: 148 },
  { name: "供应商 D", contrib: 6, abs: 47 },
  { name: "供应商 E", contrib: 9, abs: 70 },
];

export const BREAKDOWN_DATA = [
  { factor: "数量变化", impact: -68, label: "-68%" },
  { factor: "价格变化", impact: -18, label: "-18%" },
  { factor: "结构变化", impact: -14, label: "-14%" },
];

export const TABLE_ROWS: string[][] = [
  ["华东区", "上海", "28,420", "-12.3%", "供应商 A 贡献最大", "高"],
  ["华南区", "广州", "21,350", "-8.7%", "数量下降为主", "中"],
  ["华北区", "北京", "19,880", "-5.4%", "供应商 B 影响显著", "中"],
  ["西南区", "成都", "11,240", "+3.2%", "唯一正增长区域", "低"],
  ["华中区", "武汉", "8,960", "-16.1%", "结构变化明显", "高"],
];

export const ANALYSIS_PHASES_TEMPLATE = [
  "正在理解问题",
  "正在确认分析范围",
  "正在比较 2026 年 6 月和 7 月",
  "正在分析整体销售变化",
  "正在寻找主要供应商贡献",
  "正在判断数量、价格和结构变化",
  "正在检查品类差异",
  "正在整理关键发现",
];

export const DEFAULT_FINDINGS: FindingBlock[] = [
  {
    type: "text",
    id: "f1",
    content: "**总体判断**：2026 年 7 月批发销售额较 6 月下降约 **15.2%**，绝对金额减少约 **780 万元**。这一降幅超出季节性预期，主要由供应端异常集中引发，而非需求端系统性走弱。三家主要供应商合计贡献了约 88% 的降幅。",
    source: "批发销售数据库 · 2026-06 至 2026-07",
    sourceDetail: "数据范围：2026-01-01 至 2026-07-31\n分析指标：批发销售额（万元）\n比较期间：2026-06 vs 2026-07\n计算说明：环比变动 = (7月销售额 - 6月销售额) / 6月销售额 × 100%\n已知限制：部分区域数据存在 T+1 延迟",
  },
  {
    type: "chart-trend",
    id: "f2",
    title: "批发销售额月度趋势（万元）",
    data: TREND_DATA,
    source: "批发销售数据库 · 月度汇总",
    sourceDetail: "数据范围：2026-02-01 至 2026-07-31\n分析指标：月度批发销售额（万元）\n数据刷新频率：每日\n已知限制：上上月数据为最终确认版，近两月可能调整",
  },
  {
    type: "text",
    id: "f3",
    content: "**关键转折**：6 月销售额创近半年峰值（5,120 万元），7 月急剧回落至 4,340 万元。从历史规律看，7 月通常为平季，但本次降幅远超往年同期 3–5% 的正常波动范围，需重点排查供应商履约异常。",
    source: "销售分析系统 · 季节性基准",
    sourceDetail: "数据范围：2023-2025 年历史同期\n分析指标：7月环比变动率\n计算说明：历史均值 ±1σ 区间为 -5% 至 +5%，本次 -15.2% 超出 2σ 范围\n已知限制：历史数据仅包含 3 年，样本量偏少",
  },
  {
    type: "chart-contrib",
    id: "f4",
    title: "各供应商对销售额变化的贡献（%）",
    data: SUPPLIER_DATA,
    source: "供应商履约数据库 · 2026-07",
    sourceDetail: "数据范围：2026-07 供应商级别销售明细\n分析指标：各供应商销售额环比变动（万元）及贡献占比（%）\n计算说明：贡献率 = 各供应商变化量 / 总变化量 × 100%\n已知限制：供应商 D、E 数据存在小额调整可能",
  },
  {
    type: "chart-breakdown",
    id: "f5",
    title: "变化来源拆解：数量 / 价格 / 结构",
    data: BREAKDOWN_DATA,
    source: "价格与结构分析模型",
    sourceDetail: "数据范围：2026-06 至 2026-07 SKU 级别明细\n分析方法：价格-数量-结构三因素拆解法\n计算说明：总变化 = 数量效应 + 价格效应 + 结构效应\n已知限制：结构变化计算基于品类权重，存在 ±2% 误差",
  },
  {
    type: "text",
    id: "f6",
    content: "**数量主导**：本次降幅中，**数量减少贡献 68%**，平均售价变化贡献 18%，品类结构变化贡献 14%。数量下滑集中在供应商 A 和 B 的主要 SKU，价格维持稳定，结构变化主要体现在饮料品类向更低价格带偏移。",
    source: "价格与结构分析模型",
    sourceDetail: "数据范围：SKU 级别 2026-06 至 2026-07\n分析指标：数量（件）、均价（元/件）、品类权重\n计算说明：数量效应 = Σ(数量变化 × 上期均价)\n已知限制：新上线 SKU 暂未纳入结构分析",
  },
  {
    type: "table",
    id: "f7",
    title: "区域销售表现汇总",
    columns: ["区域", "核心城市", "销售额（万元）", "环比变化", "主要特征", "风险等级"],
    rows: TABLE_ROWS,
    source: "区域销售系统 · 2026-07",
    sourceDetail: "数据范围：2026-07 区域销售汇总\n分析维度：大区 / 核心城市\n已知限制：西南区部分二线城市数据尚未完整",
  },
];

export const DEFAULT_INSIGHTS = [
  "7 月销售额较 6 月下降 15.2%，超出季节性预期",
  "三家供应商合计贡献 88% 降幅",
  "数量变化是主因，占总降幅 68%",
  "西南区为唯一正增长区域（+3.2%）",
];

export const PRESET_QUESTIONS = [
  "为什么 7 月批发销售额下降？主要原因是什么？",
  "找出 Polk County 下降最大的 5 家门店，并查看明细",
  "2024 年 7 月的批发价差率是多少？",
];

export interface AiDiscovery {
  id: string;
  text: string;
  tag: string;
  analysisId: string;
  findingId: string;
}

export const AI_DISCOVERIES: AiDiscovery[] = [
  { id: "d1", text: "供应商 A 对本月下降贡献最大，占总降幅 41%", tag: "供应商", analysisId: "a1", findingId: "f4" },
  { id: "d2", text: "数量变化是目前最主要的下降来源，价格影响相对较小", tag: "数量/价格", analysisId: "a1", findingId: "f5" },
  { id: "d3", text: "饮料品类出现明显结构性变化，建议深入分析", tag: "品类", analysisId: "a1", findingId: "f6" },
  { id: "d4", text: "Polk County 区域变化仍需进一步数据确认", tag: "区域", analysisId: "a1", findingId: "f7" },
];

export const DATASET_INFO = {
  name: "Iowa 批发酒类销售数据",
  source: "Iowa Department of Commerce",
  lastUpdated: "2026-08-01",
  timeRange: "2012-01-01 至 2026-07-31",
  totalRecords: "28,456,320",
  fields: [
    { name: "invoice_item_number", label: "发票编号", type: "string" },
    { name: "date", label: "销售日期", type: "date" },
    { name: "store_number", label: "门店编号", type: "string" },
    { name: "store_name", label: "门店名称", type: "string" },
    { name: "address", label: "地址", type: "string" },
    { name: "city", label: "城市", type: "string" },
    { name: "zip_code", label: "邮编", type: "string" },
    { name: "store_location", label: "门店坐标", type: "geo" },
    { name: "county_number", label: "县区编号", type: "string" },
    { name: "county", label: "县区", type: "string" },
    { name: "category", label: "品类编码", type: "string" },
    { name: "category_name", label: "品类名称", type: "string" },
    { name: "vendor_number", label: "供应商编号", type: "string" },
    { name: "vendor_name", label: "供应商名称", type: "string" },
    { name: "item_number", label: "商品编号", type: "string" },
    { name: "item_description", label: "商品描述", type: "string" },
    { name: "pack", label: "包装规格", type: "number" },
    { name: "bottle_volume_ml", label: "瓶装容量（ml）", type: "number" },
    { name: "state_bottle_cost", label: "州采购成本（美元）", type: "currency", availableSince: "2025-07-01" },
    { name: "state_bottle_retail", label: "州零售价（美元）", type: "currency" },
    { name: "bottles_sold", label: "售出瓶数", type: "number" },
    { name: "sale_dollars", label: "批发销售额（美元）", type: "currency" },
    { name: "volume_sold_liters", label: "销售升数（L）", type: "number" },
    { name: "volume_sold_gallons", label: "销售加仑数（gallon）", type: "number" },
  ],
};

export const METRICS = [
  { id: "m1", name: "批发销售额", formula: "SUM(sale_dollars)", description: "所有批发交易的销售额总和（美元）", availableSince: "数据集起始", category: "销售", restricted: false },
  { id: "m2", name: "售出瓶数", formula: "SUM(bottles_sold)", description: "所有交易中售出的瓶数合计", availableSince: "数据集起始", category: "数量", restricted: false },
  { id: "m3", name: "销售升数", formula: "SUM(volume_sold_liters)", description: "所有销售的酒类总升数", availableSince: "数据集起始", category: "数量", restricted: false },
  { id: "m4", name: "平均批发价格", formula: "SUM(sale_dollars) / SUM(bottles_sold)", description: "每瓶的平均批发价格（美元/瓶）", availableSince: "数据集起始", category: "价格", restricted: false },
  { id: "m5", name: "州采购成本", formula: "SUM(state_bottle_cost * bottles_sold)", description: "州政府采购成本总额", availableSince: "2025-07-01", category: "成本", restricted: true },
  { id: "m6", name: "批发价差", formula: "SUM(sale_dollars) - SUM(state_bottle_cost * bottles_sold)", description: "批发销售额与州采购成本的差值", availableSince: "2025-07-01", category: "成本", restricted: true },
  { id: "m7", name: "批发价差率", formula: "(批发价差 / 批发销售额) × 100%", description: "批发价差占批发销售额的百分比", availableSince: "2025-07-01", category: "成本", restricted: true },
];

export const EVAL_CASES = [
  { id: "e1", question: "7 月销售额环比变化", expected: "下降 15.2%", result: "下降 15.2%", passed: true, latency: 2.3 },
  { id: "e2", question: "贡献最大的供应商", expected: "供应商 A（41%）", result: "供应商 A（41%）", passed: true, latency: 3.1 },
  { id: "e3", question: "下降主要来源", expected: "数量变化（68%）", result: "数量变化（68%）", passed: true, latency: 2.8 },
  { id: "e4", question: "Polk County 7月销售额", expected: "具体数值", result: "数据尚不完整", passed: false, latency: 4.2 },
  { id: "e5", question: "增长最快区域", expected: "西南区 +3.2%", result: "西南区 +3.2%", passed: true, latency: 1.9 },
  { id: "e6", question: "价格变化影响", expected: "贡献降幅 18%", result: "贡献降幅 18%", passed: true, latency: 2.5 },
];

export function createInitialAnalyses(): Analysis[] {
  return [
    {
      id: "a1",
      question: "为什么 2026 年 7 月批发销售额下降？主要原因是什么？",
      status: "done",
      createdAt: "2026-09-02T10:24:00",
      updatedAt: "2026-09-02T10:31:00",
      phases: ANALYSIS_PHASES_TEMPLATE.map((label, i) => ({ id: `a1_p${i}`, label, status: "done" as PhaseStatus })),
      currentPhaseIndex: 7,
      findings: DEFAULT_FINDINGS,
      insights: DEFAULT_INSIGHTS,
      followUps: [],
      summary: "下降主要由三家供应商贡献，数量变化是核心驱动因素",
    },
    {
      id: "a2",
      question: "哪些品类造成了主要变化？",
      status: "clarifying",
      createdAt: "2026-09-02T11:02:00",
      updatedAt: "2026-09-02T11:02:00",
      phases: ANALYSIS_PHASES_TEMPLATE.map((label, i) => ({ id: `a2_p${i}`, label, status: (i === 0 ? "done" : "waiting") as PhaseStatus })),
      currentPhaseIndex: 0,
      findings: [{ type: "text", id: "a2_f1", content: "已理解问题方向：分析各品类对 7 月销售额变化的贡献。在继续分析之前，需要确认一个关键问题。", source: "分析系统" }],
      insights: [],
      followUps: [],
      clarificationQuestion: "您希望按哪种品类分类方式分析？①大类（烈酒/葡萄酒/啤酒）②小类（威士忌/赤霞珠/IPA 等）③供应商自定义品类",
    },
    {
      id: "a3",
      question: "Polk County 最近的批发销售趋势如何？",
      status: "insufficient",
      createdAt: "2026-09-01T17:12:00",
      updatedAt: "2026-09-01T17:19:00",
      phases: ANALYSIS_PHASES_TEMPLATE.map((label, i) => ({ id: `a3_p${i}`, label, status: "done" as PhaseStatus })),
      currentPhaseIndex: 7,
      findings: [DEFAULT_FINDINGS[0], { type: "text", id: "a3_f2", content: "**依据不足**：Polk County 的 7 月数据尚未完整同步（当前完整度约 34%）。现有数据显示趋势向好，但结论置信度偏低，不建议基于此做决策。建议等待数据补全（预计 2026-09-05）后重新分析。", source: "区域数据质量系统", sourceDetail: "数据范围：Polk County 2026-07\n当前完整度：34%（1,204 / 3,541 条记录）\n数据延迟原因：区域数据仓同步延迟\n预计完整时间：2026-09-05\n建议：等待数据补全后重新分析" }],
      insights: ["当前数据完整度仅 34%，结论可靠性低", "建议 2026-09-05 后重新分析"],
      followUps: [],
      failureReason: undefined,
      summary: "数据不完整，当前结论置信度低",
    },
    {
      id: "a4",
      question: "销售额变化主要来自数量、价格还是结构变化？",
      status: "done",
      createdAt: "2026-09-01T14:30:00",
      updatedAt: "2026-09-01T14:38:00",
      phases: ANALYSIS_PHASES_TEMPLATE.map((label, i) => ({ id: `a4_p${i}`, label, status: "done" as PhaseStatus })),
      currentPhaseIndex: 7,
      findings: [DEFAULT_FINDINGS[4], DEFAULT_FINDINGS[5]],
      insights: ["数量变化贡献 68%，是最主要来源", "价格变化贡献 18%", "结构变化贡献 14%"],
      followUps: [],
      summary: "数量减少是主因（68%），价格和结构影响相对较小",
    },
    {
      id: "a5",
      question: "哪些供应商是销售额变化的主要贡献来源？",
      status: "failed",
      createdAt: "2026-09-01T09:00:00",
      updatedAt: "2026-09-01T09:01:00",
      phases: ANALYSIS_PHASES_TEMPLATE.map((label, i) => ({ id: `a5_p${i}`, label, status: (i < 2 ? "done" : i === 2 ? "running" : "waiting") as PhaseStatus })),
      currentPhaseIndex: 2,
      findings: [],
      insights: [],
      followUps: [],
      failureReason: "供应商数据接口超时（连续 3 次请求失败）。请检查数据连接后重新分析。",
    },
  ];
}
