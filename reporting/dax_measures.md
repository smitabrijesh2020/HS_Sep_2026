# Example Power BI DAX measures (designed only, not validated against a live model)

These mirror the requirement brief's examples but are corrected for the
physical model above to avoid double counting. Validate against the real
imported tables/views once a Power BI dataset exists.

```
Total Nominations =
COUNTROWS('nominations')
-- Safe as-is IF 'nominations' contains one row per nomination (it does in
-- this schema) and archived/withdrawn rows are filtered by a report-level
-- slicer or a calculated column, not baked into the measure.

Eligible Learners =
CALCULATE(
    DISTINCTCOUNT('eligibility_decisions'[nomination_id]),
    'eligibility_decisions'[status] = "Eligible"
)
-- Uses DISTINCTCOUNT on nomination_id, not COUNTROWS, because a nomination
-- can have more than one eligibility_decision row over time (re-evaluations
-- after a manual override). COUNTROWS would double count.

Seat Utilization =
VAR ActiveNominations =
    CALCULATE(
        COUNTROWS('nominations'),
        'nominations'[status] IN {"Submitted","PendingValidation","Eligible","Confirmed"}
    )
VAR TotalCapacity =
    SUMX(VALUES('batches'[batch_id]), CALCULATE(MAX('batches'[capacity])))
RETURN
    DIVIDE(ActiveNominations, TotalCapacity)
-- TotalCapacity is summed once per distinct batch (SUMX over VALUES + MAX)
-- rather than SUM('batches'[capacity]) directly, to avoid inflating the
-- denominator if the batches table is joined at a finer grain elsewhere
-- in the model (e.g. batch sessions).
```

Open question flagged for the Power BI model owner: whether `batches` will
be imported at batch grain or batch-session grain (5 touch points per batch,
per the existing BAU trackers). If session grain, `TotalCapacity` above
must use `SUMX(VALUES(...))` exactly as written, not a plain `SUM`, or
utilization will be inflated ~5x.
