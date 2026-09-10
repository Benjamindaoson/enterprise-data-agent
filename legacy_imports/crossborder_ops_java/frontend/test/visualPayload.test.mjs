import assert from 'node:assert/strict'
import test from 'node:test'
import { parseVisualPayload } from '../src/utils/visualPayload.mjs'

test('parses visual payload marker into text and chart option', () => {
  const result = parseVisualPayload('已生成图表\nVISUAL_PAYLOAD:{"kind":"echarts","option":{"series":[{"type":"line"}]}}')

  assert.equal(result.text, '已生成图表')
  assert.equal(result.chartOption.series[0].type, 'line')
})

test('returns null when no visual payload marker exists', () => {
  assert.equal(parseVisualPayload('普通回答'), null)
})
