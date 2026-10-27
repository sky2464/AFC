export const meta = {
  name: 'afc-build-slice',
  description: 'Build open slices of one project spec (S-…): afc-build per slice, afc-check when risky or asked',
  whenToUse: 'Building several slices of a project spec. Pass spec (path under the workspace plan), slices, and optional builder/checker models.',
  phases: [
    { title: 'Build', detail: 'one afc-build per slice, then review gate' },
    { title: 'Fix', detail: 'at most two fix rounds with afc-check' },
  ],
}

// args: { spec, slices: [{number, text}], start?, builder?, checker?, check?, structural?: [numbers] }
// structural lists slices that add a module, boundary, dependency or outside call; afc-architect
// writes their design note before the build and the architecture.md update after it.
const MAX_FIX_ROUNDS = 2
const spec = args.spec
const slices = args.slices || []
const builderModel = args.builder
const checkerModel = args.checker
const start = args.start || (slices[0] && slices[0].number)
const checkMode = args.check || 'risky'
const structural = new Set(args.structural || [])
if (!spec || !slices.length) throw new Error('afc-build-slice needs args.spec and args.slices')

const RISKY = [/^afc\/hooks\//, /^bin\/afc$/, /\.env/, /secrets/]
const isRisky = file => RISKY.some(re => re.test(file))

const SH_RESULT = { type: 'object', properties: { code: { type: 'number' }, out: { type: 'string' } }, required: ['code', 'out'] }
async function sh(command) {
  if (typeof shell === 'function') return await shell(command)
  const r = await agent(`Run with Bash from the project code root:\n${command}`, {
    label: 'run', phase: 'Build', schema: SH_RESULT, model: 'haiku', effort: 'low',
  })
  return r ? { code: r.code, out: r.out } : { code: 1, out: '' }
}

const SAFETY = [
  'Writes only inside the active project code path and workspace.',
  'No secrets in files.',
  'No push, branch change, force or history rewrite.',
]

const WORK_RESULT = {
  type: 'object',
  properties: { done: { type: 'boolean' }, suite: { type: 'string' }, summary: { type: 'string' } },
  required: ['done', 'suite', 'summary'],
}
const CHECK_RESULT = {
  type: 'object',
  properties: {
    pass: { type: 'boolean' },
    problems: { type: 'array', items: { type: 'object', properties: { problem: { type: 'string' }, quotes: { type: 'string' } } } },
    notes: { type: 'array', items: { type: 'string' } },
  },
  required: ['pass', 'problems', 'notes'],
}

const tag = s => `slice ${s.number}`
const buildPrompt = s => `Build ${tag(s)} for spec ${spec}.\nSlice: ${s.number}. ${s.text}\nRead resources/afc-brief.md first. Test first; commit with "${tag(s)}" in the message.`

const designPrompt = s => `${tag(s)} for spec ${spec} changes structure. Before it is built, read
plan/architecture.md and the spec, and add a short design note for this slice (two to four lines) to
the spec's Design notes. Change only that file.`

const mapPrompt = s => `${tag(s)} for spec ${spec} is built and changed structure. Run sh bin/afc index refresh,
then update plan/architecture.md (Components and Key files) to match. Change only that file. Put a
one-line note of what changed in summary; it becomes the slice record's --architecture text.`

const ARCH_RESULT = {
  type: 'object',
  properties: { done: { type: 'boolean' }, summary: { type: 'string' } },
  required: ['done', 'summary'],
}
const runArchitect = (prompt, label) => agent(prompt, {
  label, phase: 'Build', schema: ARCH_RESULT, agentType: 'afc-architect',
})

const checkPrompt = s => `Check ${tag(s)} for spec ${spec}. Run sh bin/afc review --slice "${s.number}". Quote spec lines for every problem.`

const todo = slices.filter(s => s.number >= start)
const results = []
for (const s of todo) {
  phase('Build')
  const isStructural = structural.has(s.number)
  if (isStructural) {
    const design = await runArchitect(designPrompt(s), `design ${s.number}`)
    if (!design || !design.done) {
      results.push({ slice: s.number, pass: false, stopped: 'architect did not write the design note', design })
      break
    }
  }
  const built = await agent(buildPrompt(s), {
    label: `build ${s.number}`, phase: 'Build', schema: WORK_RESULT,
    model: builderModel, agentType: 'afc-build',
  })
  if (!built || !built.done) {
    results.push({ slice: s.number, pass: false, stopped: 'builder did not finish', built })
    break
  }
  let architecture = null
  if (isStructural) {
    const mapped = await runArchitect(mapPrompt(s), `map ${s.number}`)
    architecture = mapped ? mapped.summary : null
  }
  let check = { pass: true, problems: [], notes: [] }
  if (checkMode === 'all') {
    const raw = await agent(checkPrompt(s), {
      label: `check ${s.number}`, phase: 'Build', schema: CHECK_RESULT,
      model: checkerModel, agentType: 'afc-check',
    })
    check = raw || check
  }
  results.push({ slice: s.number, pass: check.pass, architecture })
  if (!check.pass) break
}
return { spec, results, passed: results.filter(r => r.pass).map(r => r.slice) }
