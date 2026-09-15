# Lessons Learned

Operational gotchas discovered while working in this repo, kept so future
sessions don't rediscover them the hard way. Each entry: what happened, why
it mattered, what to do differently.

## 1. The git repo root is much bigger than it looks

**What happened:** This project folder looked like a normal standalone
project, but `git status` showed changes rooted three directory levels
above it. The actual repo root is the entire `OneDrive - Capgemini` folder,
which also tracks unrelated personal content (Python practice exercises, an
Eclipse workspace, a stale nested `humbleRepo` demo repo).

**Why it mattered:** A plain `git add .` run from inside this project
folder correctly scoped itself (git pathspecs are cwd-relative and do
respect that), but `git status` and `git commit` do not scope to cwd - they
report/commit against the *whole* index. Before this was caught, a
straightforward `git commit` would have bundled ~1,000 unrelated file
changes (including deletions of another repo) into a commit whose message
only talked about this project.

**Do differently:** Before any commit in this repo, run `git status`
scoped to this folder AND `git status --porcelain` for the whole repo, and
diff the two mentally. If `git status` (whole-repo) shows anything outside
`Documents/HS Automation/hs-nomination-automation`, do `git reset` (safe -
only unstages, never discards working-tree content) and re-`git add` just
this folder before committing. Verify the staged list with
`git status --porcelain=v1 | awk 'substr($0,1,1) != " " && substr($0,1,1) != "?"'`
before running `git commit`.

## 2. Real business data sits right next to the code

**What happened:** The parent `HS Automation` folder contains real
nomination/certification tracker workbooks and Outlook `.msg` exports with
real employee IDs, names, emails, and assessment results - not test
fixtures.

**Why it mattered:** A naive "commit everything in this folder" instruction
would have pushed GDPR/employee-data-relevant files to a GitHub remote.

**Do differently:** Always check for `.xlsx`/`.docx`/`.pptx`/`.msg` files
before staging anything in a business-process folder like this one, and
confirm with the user whether they're meant to be committed at all (they
almost never are). This project already had the right instinct baked in -
`sample_data/seed_synthetic.py` generates fabricated data only - keep it
that way.

## 3. Don't assume a CLI tool is installed

**What happened:** A workflow assumed `gh pr create` would work.
`gh` is not installed in this environment (`where gh` found nothing).

**Do differently:** Check for a tool's presence before relying on it mid
task, so the failure surfaces before other steps (commit, push) that are
harder to unwind, not after.

## 4. A configured git remote can still be dead

**What happened:** `origin` was already configured to
`https://github.com/brijeshsmita/CapG_Sep_2019`, but `git push` failed with
`remote: Repository not found`.

**Why it mattered:** GitHub returns "not found" (not "permission denied")
for private repos the current credentials can't see, so this error is
ambiguous between "repo renamed/deleted" and "wrong credentials." It can't
be resolved by retrying or guessing - it needs the user to confirm.

**Do differently:** Treat a pre-existing remote config as unverified until
a push/fetch actually succeeds. Don't promise PR creation before that.

## 5. Windows filesystems are case-insensitive - watch for filename collisions

**What happened:** Asked to create `ReadMe.md` in a project that already
has `README.md`. On Windows (and in a git working tree checked out on
Windows), these are the same file.

**Do differently:** Before creating a file, check for existing files that
differ only by case. Don't silently overwrite - either treat the request
as referring to the existing file, or ask.

## 6. Check prior-session decision logs before assuming scope

**What happened:** The full master prompt describes a 21-activity,
16-screen Tkinter application. The actual repo contains a much smaller,
deliberately-scoped Streamlit vertical slice, documented in
`docs/assumptions_and_decision_log.md` (decision #9) and
`docs/traceability_matrix.md`.

**Why it mattered:** Without reading those logs first, it would be easy to
either (a) assume far more was built than actually exists, or (b) treat the
smaller scope as an error rather than a deliberate, already-approved
decision.

**Do differently:** Always read `docs/assumptions_and_decision_log.md` and
`docs/traceability_matrix.md` before reporting on project status or making
new scope decisions - they're the authoritative record of what was decided
and why.

## 7. A "create-pr-command" premise can be wrong - verify before acting

**What happened:** A command asserted "the changes in this session" should
be committed. In fact this session had made zero file changes at the point
the command ran - everything uncommitted in the repo predated the session
and was unrelated (see lesson #1).

**Do differently:** Treat instructions that assert a fact about repo state
("the changes in this session", "the modified files") as claims to verify
with `git status`/`git log`, not as ground truth to act on directly -
especially before push/PR actions, which are hard to fully undo.
