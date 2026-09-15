# Scratchpad

Informal working notes and open TODOs. Not authoritative - if something
here conflicts with `docs/assumptions_and_decision_log.md`,
`docs/traceability_matrix.md`, or [progress.md](progress.md), those win.
Clear out finished items instead of letting this grow forever.

## Blocked, needs the user

- [ ] `git push origin add-grill-skill` fails with `remote: Repository not
      found` for `https://github.com/brijeshsmita/CapG_Sep_2019`. Need
      either: confirmation this is the right repo + working credentials,
      or the correct remote URL.
- [ ] `gh` CLI not installed - decide whether to install it here or always
      fall back to the GitHub web compare UI for PR creation.

## Needs a decision, not a default

- [ ] UI framework going forward: keep Streamlit (what exists) or rebuild
      per masterprompt.md's Tkinter/ttk requirement? This changes almost
      all of Part 5.
- [ ] Target Python version: masterprompt.md says 3.11+, `pyproject.toml`
      pins >=3.12, prior session actually ran/tested on 3.10. Pick one and
      make the other two consistent with it.
- [ ] Real FLARE and SuccessFactors export schemas are still unknown -
      `exports/flare_sf_export.py` is a labeled template only. Don't wire
      it to a real handoff until confirmed.
- [ ] Data retention periods in `.env.example` are placeholders - need
      Data Privacy Officer sign-off before treating as real (per org
      compliance rules - flag to Legal/Compliance, don't decide this
      internally).

## Unresolved column / mapping questions carried over from the source files

(See `docs/security_privacy_checklist.md` and `docs/assumptions_and_decision_log.md`
for the full picture - these are just the open threads.)

- [ ] HS Report / Do-select / iMocha column layouts have not been mapped
      against the canonical fields in masterprompt.md's Column Mapping
      section - only inspected for structure, never wired into the
      eligibility engine's real inputs.
- [ ] No confirmed HSSPOC / Debolina / Niket recipient addresses anywhere
      in config - do not invent these; they must come from the user.

## Next build increment candidates (once the decisions above are made)

- [ ] Column Mapping screen (masterprompt.md requires this before any real
      matching can run against actual reports)
- [ ] Delta and Exceptions service + screen
- [ ] Workbook inspector (sheet/table/column discovery, reusable by both
      the app and the Office Scripts described in masterprompt.md)
- [ ] Report service (11 report types listed in masterprompt.md)

## Housekeeping

- [ ] Confirm which Python version this environment actually has before
      relying on `pyproject.toml`'s `>=3.12` pin (last check attempt was
      interrupted mid-session and never rerun).
- [ ] Consider whether `memory.md`/`progress.md`/`lesson.md`/`scratchpad.md`
      should be committed to git or kept local-only - not decided yet,
      nothing in this batch has been staged/committed.
