Rajasthan Office Order Generator - Arrear Calculation Update

FILES
1. app.py                     -> latest application file, only arrear-section changes applied
2. arrear_calculation.py      -> arrear calculation engine changes
3. test_arrear_rules.py      -> automated tests for the requested pay-fixation/increment rules
4. app_diff.txt              -> audit diff against the source app snapshot used for this update

IMPLEMENTED
- Promotion: initial Due Basic is automatic and locked.
- Promotion fixation: one increment in old Level, then first strictly higher cell in new Level.
  Equal target cell is skipped and the next higher cell is selected.
- ACP/MACP: 9-year / 18-year / 27-year selection added.
- ACP/MACP with Level change: same fixation rule as Promotion.
- ACP/MACP without Level change: one increment in the same Level.
- Pay Fixation: no automatic fixation logic; operator enters Due Basic manually.
- Regular increment is applied to the correct month's row (not one month late).
- Six-month service test used for the next regular increment after a Level change was corrected.
- Deduction input fields grouped as GPF, SI, RGHS, then Income Tax/Other.
- Existing arrear PDF rendering code was not changed.
- PL Surrender, Sanchalan Portal, and Annual Increment sections were not modified except for the arrear import/helper import needed by the arrear section.

TESTING
- Python syntax compilation passed for app.py and arrear_calculation.py.
- test_arrear_rules.py passed.
- Full 7th Pay Matrix fixation example L-11 42500 -> L-12 44300 passed.
- Equal-cell rule test passed: equal target cell is skipped.
- ACP/MACP level-change and same-level tests passed.
- Pay Fixation manual/no-auto-rule test passed.
- Same-month fixation double-increment prevention test passed.
- Full Pay Matrix annual progression test passed.

IMPORTANT: OFFICE ORDER GENERATION
The office-order generation for Promotion and ACP/MACP is NOT fabricated in this package because the exact office-order formats/templates have not yet been supplied in the current request. Once the actual Promotion and ACP/MACP office-order formats are uploaded, they can be integrated using the already-stored reason, order date, employee details, old/new Pay Level, initial Due Basic, and ACP/MACP tenure fields without changing the arrear PDF format or the other three modules.
