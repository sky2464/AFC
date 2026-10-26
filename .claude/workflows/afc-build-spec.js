export const meta = {
  name: 'afc-build-spec',
  description: 'Build the slices of one Flight Control spec: one builder per slice, a code gate after it, a checker only for risky slices or when asked for a full check, at most two fix rounds',
  whenToUse: 'Building several slices of a Flight Control spec (FC-…) in maintenance mode. Pass spec, slices and models; do not write a new script.',
  phases: [
    { title: 'Build', detail: 'one builder per slice, then the quick gate; the checker for risky slices' },
    { title: 'Fix', detail: 'one fixer plus one checker per round, at most two rounds' },
  ],
}

// args: { spec, slices: [{number, text}], start?, alreadyBuilt?: [numbers], builder?, checker?, check?, structural?: [numbers] }
// spec is the spec's path (or ID), slices its slice lines; builder/checker are model names.
// check is 'risky' (default: the checker runs only for risky slices) or 'all' (every slice).
// There is no way to turn checking off: risky slices are always checked.
// structural lists the slices that add a module, boundary, dependency or outside call: afc-architect
// writes a design note before each of them, and after any slice whose build leaves an unmapped module.
const MAX_FIX_ROUNDS = 2

const spec = args.spec
const slices = args.slices || []
const builderModel = args.builder
const checkerModel = args.checker
const start = args.start || (slices[0] && slices[0].number)
const alreadyBuilt = new Set(args.alreadyBuilt || [])
const structural = new Set(args.structural || [])
const checkMode = args.check || 'risky'
if (!spec || !slices.length) throw new Error('afc-build-spec needs args.spec and args.slices')
if (checkMode !== 'risky' && checkMode !== 'all') throw new Error("args.check must be 'risky' or 'all'")

// The one list of risky paths: the guards and hooks, maintenance mode, git and delivery, update
// apply, the remote, anything that reads secrets, and the build machinery itself.
const RISKY = [
  /^afc\/hooks\//,
  /^bin\/afc$/,
  /^\.claude\/(settings[^/]*\.json|agents\/|workflows\/)/,
  /^afc\/(git_ops|ship|undo|update|update_apply|secrets|scan|rules|tools|profile|config)\.py$/,
  /^afc\/cli_(ship|delivery|maintain|tools|home)\.py$/,
  /^afc\/.*remote/,
]
const isRisky = file => RISKY.some(re => re.test(file))

// sh(command) -> {code, out}. The runtime has no shell, so a cheap helper runs the command and
// returns its exit code and output word for word. Tests supply `shell` instead.
const SH_RESULT = {
  type: 'object',
  properties: { code: { type: 'number' }, out: { type: 'string' } },
  required: ['code', 'out'],
}
async function sh(command) {
  if (typeof shell === 'function') return await shell(command)
  const r = await agent(
    `Run this one command from the repo root with Bash. Put its stdout in "out" exactly as printed, ` +
    `adding no words, and its exit status in "code":\n${command}`,
    { label: 'run: ' + command.slice(0, 40), phase: 'Build', schema: SH_RESULT, model: 'haiku', effort: 'low' })
  return r ? { code: r.code, out: r.out } : { code: 1, out: '' }
}
const q = s => JSON.stringify(String(s))

const SAFETY = [
  'Writes only inside this repo and the Flight Control home (~/.A-FC).',
  'No secrets in any file.',
  'No push, branch change, force or history rewrite.',
  'The maintenance-mode guard is not bypassed or weakened.',
]

const WORK_RESULT = {
  type: 'object',
  properties: {
    done: { type: 'boolean' },
    commits: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['done', 'summary'],
}

const CHECK_RESULT = {
  type: 'object',
  properties: {
    pass: { type: 'boolean' },
    problems: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          problem: { type: 'string' },
          quotes: { type: 'string', description: 'the spec line or safety rule it breaks, word for word' },
        },
        required: ['problem', 'quotes'],
      },
    },
    notes: { type: 'array', items: { type: 'string' } },
  },
  required: ['pass', 'problems', 'notes'],
}

const tag = s => `slice ${s.number}`

const buildPrompt = s => `Build ${tag(s)} of the spec at ${spec}.

Slice: ${s.number}. ${s.text}

Read the spec first. Build only this slice. Try the change for real (run the command, start the hook) before
committing; run no tests. Commit on the current branch with a message that contains "${tag(s)}" and the spec ID.
Tick the slice's checkbox in the spec in the same commit. Do not push or change branch.`

const fixPrompt = (s, problems, round) => `Fix ${tag(s)} of the spec at ${spec} (fix round ${round}).

Slice: ${s.number}. ${s.text}

The checker found these problems; each quotes the spec line or rule it breaks:
${problems.map(p => `- ${p.problem} (quotes: "${p.quotes}")`).join('\n')}

Fix only these. Try the fix for real before committing; run no tests. Commit with a message that
contains "${tag(s)}" and the spec ID. Do not push or change branch.`

const checkPrompt = s => `Check ${tag(s)} of the spec at ${spec}. Change nothing.

Slice: ${s.number}. ${s.text}

1. Read every commit for this slice: git log --grep "${tag(s)}" -p.
2. Judge them against the slice line, the spec's "You'll know it works when" lines, and these rules:
${SAFETY.map(r => `   - ${r}`).join('\n')}

Every problem must quote, word for word, the spec line or rule it breaks. Anything you cannot tie
to a quoted line goes in notes, not problems. Run no tests. pass is true only when there are no
problems.`

const designPrompt = s => `${tag(s)} of the spec at ${spec} changes structure. Before it is built:

Slice: ${s.number}. ${s.text}

Read docs/architecture.md and the spec. Add a short design note for this slice (two to four lines:
where the new piece lives, what it depends on, what must not depend on it) to the spec's Design notes.
Change nothing else. Commit with a message that contains "${tag(s)}" and the spec ID. Do not push or change branch.`

const mapPrompt = (s, unmapped) => `The build of ${tag(s)} of the spec at ${spec} left paths that no
Key files cell in docs/architecture.md names:
${unmapped.map(u => `- ${u}`).join('\n')}

Add each to the right row of the Components table (or a new row), then run sh bin/afc check and make
sure no architecture_unmapped is left. Change nothing else. Commit with a message that contains
"${tag(s)}" and the spec ID. Do not push or change branch. Put a one-line note of what changed in summary.`

const runArchitect = (prompt, label) => agent(prompt, {
  label, phase: 'Build', schema: WORK_RESULT, agentType: 'afc-architect',
})

async function unmappedPaths() {
  const c = lastJson((await sh('sh bin/afc check')).out)
  return ((c && c.problems) || [])
    .filter(p => p.kind === 'architecture_unmapped')
    .map(p => (String(p.detail).match(/`([^`]+)`/) || [, p.detail])[1])
}

const runChecker = (s, label, phaseName) => agent(checkPrompt(s), {
  label, phase: phaseName, schema: CHECK_RESULT, model: checkerModel, agentType: 'afc-checker',
})

// A problem that quotes nothing is a note; it does not start a fix round.
function sortProblems(check) {
  const problems = [], notes = [...(check.notes || [])]
  for (const p of check.problems || []) {
    if (p.quotes && p.quotes.trim()) problems.push(p)
    else notes.push(p.problem)
  }
  return { ...check, problems, notes, pass: check.pass && problems.length === 0 }
}

// The quick gate runs as `sh bin/afc gate`: one helper call, one JSON line back.
function lastJson(text) {
  for (const line of String(text).split('\n').reverse()) {
    const t = line.trim()
    if (t.startsWith('{') && t.endsWith('}')) { try { return JSON.parse(t) } catch (e) { /* keep looking */ } }
  }
  return null
}
async function quickGate(s, base) {
  const run = await sh(`sh bin/afc gate --spec ${q(spec)} --slice ${s.number} --base ${q(base)}`)
  const g = lastJson(run.out)
  if (!g) return { ok: false, files: [], problems: [{ problem: 'the gate gave no result: ' + String(run.out).slice(-200), quotes: 'commit tagged with the slice' }] }
  return { ok: !!g.ok, files: g.files || [], problems: g.problems || [] }
}

const results = []
const sliceFiles = {}
const todo = slices.filter(s => s.number >= start && !alreadyBuilt.has(s.number))
log(`Building ${todo.length} slice(s) of ${spec}`)

// The build moves the plan itself: the spec goes to Now before the first slice and to Done after the
// last gate passes. A spec already in Now (a resumed build) makes start say so; the build goes on.
// Each plan move is committed on the spot, so the tree is clean between slices and when the build
// ends. Only the plan's own files are staged: the plan, the specs (and their archive), and the
// changelog that `plan done` writes.
const PLAN_FILES = ['docs/master-plan.md', 'docs/specs']
async function commitPlan(message, files) {
  const paths = files.map(q).join(' ')
  const r = await sh(`git add -- ${paths} && (git diff --cached --quiet -- ${paths} || git commit -m ${q(message)} -- ${paths})`)
  return r.code === 0 ? 'committed' : 'not committed: ' + String(r.out).slice(-200)
}

const specId = (String(spec).match(/FC-\d+/) || [''])[0]
let plan = null
if (specId) {
  const started = await sh(`sh bin/afc plan start ${specId}`)
  plan = { start: started.code === 0 ? 'started' : 'not started: ' + String(started.out).slice(-200) }
  if (started.code === 0) plan.startCommit = await commitPlan(`docs: ${specId} started`, PLAN_FILES)
  log(`Plan: ${specId} ${plan.start}`)
}

for (const s of todo) {
  phase('Build')
  const base = ((await sh('git rev-parse HEAD')).out.match(/[0-9a-f]{40}/) || [''])[0]
  let design = null
  if (structural.has(s.number)) {
    design = await runArchitect(designPrompt(s), `design ${s.number}`)
    if (!design || !design.done) {
      results.push({ slice: s.number, pass: false, stopped: 'architect did not write the design note', design })
      log(`Stopped at slice ${s.number}: the architect did not finish the design note`)
      break
    }
  }
  const built = await agent(buildPrompt(s), {
    label: `build ${s.number}`, phase: 'Build', schema: WORK_RESULT,
    model: builderModel, agentType: 'afc-builder',
  })
  if (!built || !built.done) {
    results.push({ slice: s.number, pass: false, stopped: 'builder did not finish', built })
    log(`Stopped at slice ${s.number}: the builder did not finish`)
    break
  }

  let check = null
  for (let round = 0; ; round++) {
    const gate = await quickGate(s, base)
    sliceFiles[s.number] = gate.files
    const checked = checkMode === 'all' || gate.files.some(isRisky)
    if (!gate.ok) {
      check = { pass: false, problems: gate.problems, notes: ['quick gate failed'] }
    } else if (!checked) {
      check = { pass: true, problems: [], notes: ['quick gate passed; not risky, no checker'] }
    } else {
      const raw = await runChecker(s, round ? `check ${s.number}.${round}` : `check ${s.number}`, round ? 'Fix' : 'Build')
      check = raw ? sortProblems(raw) : { pass: false, problems: [], notes: ['checker did not return'] }
    }
    if (check.pass || round >= MAX_FIX_ROUNDS || !check.problems.length) break
    phase('Fix')
    const fixed = await agent(fixPrompt(s, check.problems, round + 1), {
      label: `fix ${s.number}.${round + 1}`, phase: 'Fix', schema: WORK_RESULT,
      model: builderModel, agentType: 'afc-builder',
    })
    if (!fixed || !fixed.done) break
  }

  let architecture = null
  if (check.pass) {
    const unmapped = await unmappedPaths()
    if (unmapped.length) {
      const mapped = await runArchitect(mapPrompt(s, unmapped), `map ${s.number}`)
      architecture = mapped ? mapped.summary : null
      if (!mapped || !mapped.done || (await unmappedPaths()).length) {
        check = { ...check, pass: false, notes: [...(check.notes || []), 'architect left unmapped paths'] }
      }
    }
  }

  results.push({ slice: s.number, pass: check.pass, problems: check.problems, notes: check.notes,
    design: design ? design.summary : null, architecture })
  if (!check.pass) {
    log(`Stopped at slice ${s.number}: it did not pass after ${MAX_FIX_ROUNDS} fix rounds`)
    break
  }
}

const passed = results.filter(r => r.pass).map(r => r.slice)
// Done only when every slice of the spec passed in this run or was built before it.
const allPassed = slices.every(s => alreadyBuilt.has(s.number) || passed.includes(s.number))
if (specId && allPassed) {
  const closed = await sh(`sh bin/afc plan done ${specId}`)
  plan = { ...plan, done: closed.code === 0 ? 'done' : 'not done: ' + String(closed.out).slice(-200) }
  if (closed.code === 0) plan.doneCommit = await commitPlan(`docs: ${specId} done, archived`, [...PLAN_FILES, 'docs/changelog.md'])
  log(`Plan: ${specId} ${plan.done}`)
}

return { spec, results, passed, plan }
