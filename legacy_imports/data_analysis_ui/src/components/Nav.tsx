import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/today", label: "今日", icon: "○" },
  { to: "/analyses", label: "分析", icon: "◇" },
  { to: "/data", label: "数据", icon: "▣" },
  { to: "/metrics", label: "指标口径", icon: "≡" },
  { to: "/evaluation", label: "评测", icon: "◎" },
];

export function Nav() {
  return (
    <nav className="w-14 shrink-0 bg-white border-r border-[#e4e7ec] flex flex-col items-center py-4 gap-1 z-10">
      <div className="w-8 h-8 rounded-lg bg-[#00897b] flex items-center justify-center mb-4 shrink-0">
        <span className="text-white text-[11px] font-bold font-mono">AI</span>
      </div>
      {NAV_ITEMS.map((item) => (
        <NavLink key={item.to} to={item.to} title={item.label}
          className={({ isActive }) => `w-10 h-10 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-colors ${isActive ? "bg-[#e0f2f1] text-[#00897b]" : "text-[#9ca3af] hover:bg-[#f4f5f7] hover:text-[#374151]"}`}>
          <span className="text-base leading-none">{item.icon}</span>
          <span className="text-[8px] leading-none font-medium">{item.label}</span>
        </NavLink>
      ))}
      <div className="flex-1" />
      <NavLink to="/settings" title="设置"
        className={({ isActive }) => `w-10 h-10 rounded-lg flex flex-col items-center justify-center gap-0.5 transition-colors ${isActive ? "bg-[#e0f2f1] text-[#00897b]" : "text-[#9ca3af] hover:bg-[#f4f5f7] hover:text-[#374151]"}`}>
        <span className="text-base leading-none">⊙</span>
        <span className="text-[8px] leading-none font-medium">设置</span>
      </NavLink>
    </nav>
  );
}
