// Invariants for canvas-frames.json, in the style of quantlink-inc/canvas lib/**/*.check.ts.
// Run: node canvas_frames.check.mjs
import { readFileSync } from 'node:fs'

const KINDS = new Set(['note', 'map', 'qast', 'lab1', 'page', 'dags', 'endpoints', 'data', 'loop', 'tasks', 'sheet', 'notebook', 'doc', 'slide', 'components', 'builder'])
const TYPES = new Set(['Stack', 'Heading', 'Text', 'Metric', 'Sheet'])
const eq = (a, b, label) => { if (a !== b) throw new Error(`${label}: ${String(a)} !== ${String(b)}`) }

const frames = JSON.parse(readFileSync(new URL('./canvas-frames.json', import.meta.url), 'utf8'))
eq(frames.length > 0, true, 'has frames')
eq(new Set(frames.map((f) => f.id)).size, frames.length, 'unique frame ids')
for (const f of frames) {
  eq(KINDS.has(f.kind), true, `${f.id} kind`)
  for (const k of ['x', 'y', 'w', 'h']) eq(Number.isFinite(f[k]), true, `${f.id}.${k}`)
  eq(f.spec.root in f.spec.elements, true, `${f.id} root exists`)
  for (const [id, el] of Object.entries(f.spec.elements)) {
    eq(TYPES.has(el.type), true, `${f.id}/${id} type ${el.type}`)
    for (const c of el.children) eq(c in f.spec.elements, true, `${f.id}/${id} child ${c} resolves`)
  }
}
for (let i = 0; i < frames.length; i++) for (let j = i + 1; j < frames.length; j++) {
  const a = frames[i], b = frames[j]
  eq(a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h, false, `${a.id} overlaps ${b.id}`)
}
console.log('canvas_frames.check ok')
