const VISUAL_MARKER = 'VISUAL_PAYLOAD:'

export function parseVisualPayload(content) {
  const index = content.indexOf(VISUAL_MARKER)
  if (index < 0) return null

  const raw = content.slice(index + VISUAL_MARKER.length).trim()
  const parsed = JSON.parse(raw)
  return {
    text: content.slice(0, index).trim() || '已生成可视化结果：',
    chartOption: parsed.option || parsed,
  }
}
