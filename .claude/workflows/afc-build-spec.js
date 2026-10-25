export const meta = {
  name: 'afc-build-spec',
  description: 'Build the slices of one Flight Control spec: one builder per slice, a code gate after it, a checker only for risky slices or when asked for a full check, at most two fix rounds',
  whenToUse: 'Building several slices of a Flight Control spec (FC-…) in maintenance mode. Pass spec, slices and models; do not write a new script.',
  phases: [
    { title: 'Build', detail: 'one builder per slice, then the quick gate; the checker for risky slices' },
    { title: 'Fix', detail: 'one fixer plus one checker per round, at most two rounds' },
    { title: 'Final suite', detail: 'the full suite once at the end; a failure goes to the slice whose commits changed the failing test\'s code' },
  ],
}

// args: { spec, slices: [{number, text}], start?, alreadyBuilt?: [numbers], builder?, checker?, check? }
// spec is the spec's path (or ID), slices its slice lines; builder/checker are model names.
// check is 'risky' (default: the checker runs only for risky slices) or 'all' (every slice).
// There is no way to turn checking off: risky slices are always checked.
const MAX_FIX_ROUNDS = 2

const spec = args.spec
const slices = args.slices || []
const builderModel = args.builder
const checkerModel = args.checker
const start = args.start || (slices[0] && slices[0].number)
const alreadyBuilt = new Set(args.alreadyBuilt || [])
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
    suite: { type: 'string', description: 'last lines of the full test suite run before the commit' },
    summary: { type: 'string' },
  },
  required: ['done', 'suite', 'summary'],
}

const CHECK_RESULT = {
  type: 'object',
  properties: {
    pass: { type: 'boolean' },
    suite: { type: 'string', description: 'last lines of the suite run by the checker' },
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
  required: ['pass', 'suite', 'problems', 'notes'],
}

const tag = s => `slice ${s.number}`

const buildPrompt = s => `Build ${tag(s)} of the spec at ${spec}.

Slice: ${s.number}. ${s.text}

Read the spec first. Build only this slice, test first. Run "sh bin/afc test --changed <the commit before your work>" before
committing (the workflow runs the full suite once at the end); commit on the current branch with a message that contains "${tag(s)}" and the spec ID.
Tick the slice's checkbox in the spec in the same commit. Do not push or change branch.
Return the suite's last lines.`

const fixPrompt = (s, problems, round) => `Fix ${tag(s)} of the spec at ${spec} (fix round ${round}).

Slice: ${s.number}. ${s.text}

The checker found these problems; each quotes the spec line or rule it breaks:
${problems.map(p => `- ${p.problem} (quotes: "${p.quotes}")`).join('\n')}

Fix only these. Run "sh bin/afc test --changed <the commit before your fix>" before committing; commit with a message that
contains "${tag(s)}" and the spec ID. Do not push or change branch. Return the suite's last lines.`

const checkPrompt = (s, builderSuite) => `Check ${tag(s)} of the spec at ${spec}. Change nothing.

Slice: ${s.number}. ${s.text}

1. Run the full test suite yourself; the builder's report below is not the check.
2. Read every commit for this slice: git log --grep "${tag(s)}" -p.
3. Judge them against the slice line, the spec's "You'll know it works when" lines, and these rules:
${SAFETY.map(r => `   - ${r}`).join('\n')}

Every problem must quote, word for word, the spec line or rule it breaks. Anything you cannot tie
to a quoted line goes in notes, not problems. pass is true only when the suite passes and there
are no problems.

Builder's suite report:
${builderSuite || '(none)'}`

const runChecker = (s, report, label, phaseName) => agent(checkPrompt(s, report), {
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

for (const s of todo) {
  phase('Build')
  const base = ((await sh('git rev-parse HEAD')).out.match(/[0-9a-f]{40}/) || [''])[0]
  const built = await agent(buildPrompt(s), {
    label: `build ${s.number}`, phase: 'Build', schema: WORK_RESULT,
    model: builderModel, agentType: 'afc-builder',
  })
  if (!built || !built.done) {
    results.push({ slice: s.number, pass: false, stopped: 'builder did not finish', built })
    log(`Stopped at slice ${s.number}: the builder did not finish`)
    break
  }

  let report = built.suite
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
      const raw = await runChecker(s, report, round ? `check ${s.number}.${round}` : `check ${s.number}`, round ? 'Fix' : 'Build')
      check = raw ? sortProblems(raw) : { pass: false, problems: [], notes: ['checker did not return'] }
    }
    if (check.pass || round >= MAX_FIX_ROUNDS || !check.problems.length) break
    phase('Fix')
    const fixed = await agent(fixPrompt(s, check.problems, round + 1), {
      label: `fix ${s.number}.${round + 1}`, phase: 'Fix', schema: WORK_RESULT,
      model: builderModel, agentType: 'afc-builder',
    })
    if (!fixed || !fixed.done) break
    report = fixed.suite
  }

  results.push({ slice: s.number, pass: check.pass, problems: check.problems, notes: check.notes })
  if (!check.pass) {
    log(`Stopped at slice ${s.number}: it did not pass after ${MAX_FIX_ROUNDS} fix rounds`)
    break
  }
}

// The full suite, once, after the last slice. Returns {ok, failures, tail}.
async function fullSuite() {
  const run = await sh('sh bin/afc test')
  let report = null
  for (const line of run.out.split('\n').reverse()) {
    try { report = JSON.parse(line); break } catch (e) { /* not the JSON line */ }
  }
  const failures = (report && report.failures) || []
  const ok = run.code === 0 && failures.length === 0 && (!report || !report.failed)
  return { ok, failures, tail: run.out.trim().split('\n').slice(-3).join('\n') }
}

// Which built slice owns a failing test: the one whose commits changed the test file itself or
// code the test imports or names. If none matches, the last slice built.
async function ownerOf(failure, built) {
  const file = String(failure).split(':')[0].trim()
  const text = (await sh(`cat ${q('tests/' + file)} | grep -oE '[A-Za-z0-9_./]+[.](py|js|md)|afc[A-Za-z0-9_.]*'`)).out
  for (const s of built) {
    for (const f of sliceFiles[s.number] || []) {
      const mod = f.replace(/\.py$/, '').replace(/\//g, '.')
      if (f === 'tests/' + file || (f.endsWith('.py') && text.includes(mod)) || text.includes(f)) return s
    }
  }
  return built[built.length - 1]
}

let finalSuite = null
const builtSlices = todo.filter(s => results.some(r => r.slice === s.number && r.pass))
if (builtSlices.length && builtSlices.length === todo.length) {
  phase('Final suite')
  finalSuite = await fullSuite()
  for (let round = 1; !finalSuite.ok && round <= MAX_FIX_ROUNDS; round++) {
    const owner = await ownerOf(finalSuite.failures[0] || '', builtSlices)
    phase('Fix')
    const problems = (finalSuite.failures.length ? finalSuite.failures : [finalSuite.tail]).map(f => ({
      problem: `the final full suite fails: ${f}`, quotes: 'the full suite runs once. If it fails',
    }))
    const fixed = await agent(fixPrompt(owner, problems, round), {
      label: `fix ${owner.number}.final${round}`, phase: 'Fix', schema: WORK_RESULT,
      model: builderModel, agentType: 'afc-builder',
    })
    if (!fixed || !fixed.done) break
    const raw = await runChecker(owner, fixed.suite, `check ${owner.number}.final${round}`, 'Fix')
    finalSuite = await fullSuite()
    finalSuite.checker = raw ? sortProblems(raw).pass : false
    log(`Final suite after round ${round}: ${finalSuite.ok ? 'passes' : 'still fails'}`)
  }
  if (!finalSuite.ok) log('The final full suite still fails')
}

return { spec, finalSuite, results, passed: results.filter(r => r.pass).map(r => r.slice) }
