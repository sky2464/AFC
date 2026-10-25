export const meta = {
  name: 'afc-build-spec',
  description: 'Build the slices of one Flight Control spec: one builder per slice, a code gate after it, a checker only for risky slices or when asked for a full check, at most two fix rounds',
  whenToUse: 'Building several slices of a Flight Control spec (FC-…) in maintenance mode. Pass spec, slices and models; do not write a new script.',
  phases: [
    { title: 'Build', detail: 'one builder per slice, then the quick gate; the checker for risky slices' },
    { title: 'Fix', detail: 'one fixer plus one checker per round, at most two rounds' },
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

// Secret patterns the gate looks for in added lines of the diff.
const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\bgh[pousr]_[A-Za-z0-9]{30,}\b/,
  /\bsk-[A-Za-z0-9_-]{20,}\b/,
  /\bxox[abprs]-[A-Za-z0-9-]{10,}\b/,
]

// sh(command) -> {code, out}. The runtime may supply `shell`; otherwise use node's child_process.
async function sh(command) {
  if (typeof shell === 'function') return await shell(command)
  const { spawnSync } = await import('node:child_process')
  const r = spawnSync('sh', ['-c', command], { encoding: 'utf8' })
  return { code: r.status, out: (r.stdout || '') + (r.stderr || '') }
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

Read the spec first. Build only this slice, test first. Run the full test suite once before
committing; commit on the current branch with a message that contains "${tag(s)}" and the spec ID.
Tick the slice's checkbox in the spec in the same commit. Do not push or change branch.
Return the suite's last lines.`

const fixPrompt = (s, problems, round) => `Fix ${tag(s)} of the spec at ${spec} (fix round ${round}).

Slice: ${s.number}. ${s.text}

The checker found these problems; each quotes the spec line or rule it breaks:
${problems.map(p => `- ${p.problem} (quotes: "${p.quotes}")`).join('\n')}

Fix only these. Run the full test suite once before committing; commit with a message that
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

// A problem that quotes nothing is a note; it does not start a fix round.
function sortProblems(check) {
  const problems = [], notes = [...(check.notes || [])]
  for (const p of check.problems || []) {
    if (p.quotes && p.quotes.trim()) problems.push(p)
    else notes.push(p.problem)
  }
  return { ...check, problems, notes, pass: check.pass && problems.length === 0 }
}

// The quick gate: code, no helper. Returns {ok, problems, files}; each problem quotes its rule.
async function quickGate(s, base) {
  const problems = []
  const add = (problem, quotes) => problems.push({ problem, quotes })
  const names = await sh(`git diff --name-only ${q(base)} HEAD`)
  const files = names.out.split('\n').map(f => f.trim()).filter(Boolean)

  const commits = await sh(`git log --format=%H --grep ${q(tag(s))} ${q(base)}..HEAD`)
  if (commits.code !== 0 || !commits.out.trim()) {
    add(`no commit since ${base.slice(0, 7)} has "${tag(s)}" in its message`, 'commit tagged with the slice')
  }

  const specText = await sh(`cat ${q(spec)}`)
  const ticked = new RegExp(`^- \\[x\\] ${s.number}\\.`, 'm')
  if (!ticked.test(specText.out)) add(`slice ${s.number}'s checkbox is not ticked in ${spec}`, 'checkbox ticked')

  const tests = await sh(`sh bin/afc test --changed ${q(base)}`)
  if (tests.code !== 0) {
    add(`the slice's tests fail: ${tests.out.trim().split('\n').slice(-3).join(' | ')}`, "the slice's tests pass")
  }

  const diff = await sh(`git diff ${q(base)} HEAD`)
  const added = diff.out.split('\n').filter(l => l.startsWith('+') && !l.startsWith('+++'))
  if (added.some(l => SECRET_PATTERNS.some(re => re.test(l)))) {
    add('the diff adds a line that looks like a secret', 'no secret patterns in the diff')
  }

  const outside = files.filter(f => f.startsWith('/') || f.split('/').includes('..'))
  if (outside.length) add(`files outside this repo: ${outside.join(', ')}`, 'no file changed outside this repo')

  return { ok: problems.length === 0, problems, files }
}

const results = []
const todo = slices.filter(s => s.number >= start && !alreadyBuilt.has(s.number))
log(`Building ${todo.length} slice(s) of ${spec}`)

for (const s of todo) {
  phase('Build')
  const base = (await sh('git rev-parse HEAD')).out.trim()
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
    const checked = checkMode === 'all' || gate.files.some(isRisky)
    if (!gate.ok) {
      check = { pass: false, problems: gate.problems, notes: ['quick gate failed'] }
    } else if (!checked) {
      check = { pass: true, problems: [], notes: ['quick gate passed; not risky, no checker'] }
    } else {
      const raw = await agent(checkPrompt(s, report), {
        label: round ? `check ${s.number}.${round}` : `check ${s.number}`,
        phase: round ? 'Fix' : 'Build', schema: CHECK_RESULT,
        model: checkerModel, agentType: 'afc-checker',
      })
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

return { spec, results, passed: results.filter(r => r.pass).map(r => r.slice) }
