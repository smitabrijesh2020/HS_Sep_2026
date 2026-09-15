# Security and Privacy Checklist

## Findings from the source folder (for awareness - no PII copied here)
- Real employee IDs, names, emails, manager emails, grades, and
  certification/assessment results exist in the BAU trackers
  (`Nominations - Aug 2026_5.0_To_Share.xlsx`, `Hyperscalers Certifications
  Data - 17_Jul_2026.xlsx`, `BAU Test Report_10-08-2026.xlsx`,
  `Hyperscalers Certification Training Registration Form...xlsx`). These
  are GDPR/employee-data-relevant. None of this data was copied into code,
  tests, seed data, or this documentation.
- No hard-coded credentials, SMTP passwords, tokens, or connection strings
  were found in any of the reviewed files (they are Office documents/data
  exports, not code or config).
- The `.msg` mail templates confirm a hard eligibility gate exists today
  (prerequisite test not cleared -> nomination cancelled) and a
  first-come-first-served batch-fill pattern - both reflected in this
  build's eligibility engine and nomination service.

## Controls implemented in this slice
- [x] Synthetic data only in `sample_data/seed_synthetic.py` (fabricated names/emails)
- [x] UUID primary keys everywhere (no sequential IDs exposed)
- [x] Parameterized SQL only (`sqlite3` with `?` placeholders) - no string-built queries
- [x] Missing/unavailable eligibility source data routes to `PendingCriteria`,
      never to an automatic adverse (`NotEligible`) decision
- [x] Manual eligibility overrides require actor + reason + timestamp and are
      appended (never overwrite) the automated result
- [x] Communication error details pass through a redaction filter
      (`_sanitize_error`) before storage
- [x] No real Microsoft Graph network call is wired in; dry-run is the only
      exercised path
- [x] `.env.example` contains placeholder values only

## Controls designed but NOT yet implemented / need organizational input
- [ ] Role-based access control and field-level PII masking in the Streamlit
      UI (the 9-role matrix in your Dataverse doc is the reference; this
      slice has no login/identity page yet)
- [ ] Encryption at rest for the production database (SQLite file has none by default)
- [ ] Confirmed Graph permission scope + delegated-vs-application decision
      from the tenant admin (recommended: application permission `Mail.Send`,
      certificate-based auth, least privilege)
- [ ] Data retention periods - placeholders in `.env.example` need Data
      Privacy Officer approval
- [ ] A DPIA/privacy review before any real employee data is loaded

## Stop-and-ask triggers that were respected this session
No production secrets were requested or entered; no real employee data was
loaded into the running app; no tenant permissions were touched; no
destructive database operation was run; no email was sent.
