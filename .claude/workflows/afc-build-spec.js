export const meta = {
  name: 'afc-build-spec',
  description: 'Build the slices of one Flight Control spec: one builder and one checker per slice, at most two fix rounds',
  whenToUse: 'Building several slices of a Flight Control spec (FC-…) in maintenance mode. Pass spec, slices and models; do not write a new script.',
  phases: [
    { title: 'Build', detail: 'one builder per slice, then one checker' },
    { title: 'Fix', detail: 'one fixer plus one checker per round, at most two rounds' },
  ],
}

// args: { spec, slices: [{number, text}], start?, alreadyBuilt?: [numbers], builder?, checker? }
// spec is the spec's path (or ID), slices its slice lines; builder/checker are model names.
const MAX_FIX_ROUNDS = 2

const spec = args.spec
const slices = args.slices || []
const builderModel = args.builder
const checkerModel = args.checker
const start = args.start || (slices[0] && slices[0].number)
const alreadyBuilt = new Set(args.alreadyBuilt || [])
if (!spec || !slices.length) throw new Error('afc-build-spec needs args.spec and args.slices')

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

const results = []
const todo = slices.filter(s => s.number >= start && !alreadyBuilt.has(s.number))
log(`Building ${todo.length} slice(s) of ${spec}`)

for (const s of todo) {
  phase('Build')
  const built = await agent(buildPrompt(s), {
    label: `build ${s.number}`, phase: 'Build', schema: WORK_RESULT,
    model: builderModel,
  })
  if (!built || !built.done) {
    results.push({ slice: s.number, pass: false, stopped: 'builder did not finish', built })
    log(`Stopped at slice ${s.number}: the builder did not finish`)
    break
  }

  let report = built.suite
  let check = null
  for (let round = 0; ; round++) {
    const raw = await agent(checkPrompt(s, report), {
      label: round ? `check ${s.number}.${round}` : `check ${s.number}`,
      phase: round ? 'Fix' : 'Build', schema: CHECK_RESULT,
      model: checkerModel,
    })
    check = raw ? sortProblems(raw) : { pass: false, problems: [], notes: ['checker did not return'] }
    if (check.pass || round >= MAX_FIX_ROUNDS || !check.problems.length) break
    phase('Fix')
    const fixed = await agent(fixPrompt(s, check.problems, round + 1), {
      label: `fix ${s.number}.${round + 1}`, phase: 'Fix', schema: WORK_RESULT,
      model: builderModel,
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
