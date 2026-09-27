FINAL UPDATE - Rajasthan Office Order Generator

This update preserves the existing app interface and other modules and moves all salary-arrear calculation logic into arrear_calculation.py.

app.py:
- Existing modules remain in place.
- Salary Arrear page collects inputs, calls calculate_arrear(), stores returned results, and renders the report.
- No arrear calculation loop remains in app.py.

arrear_calculation.py:
- DA/cash DA/GPF-credit schedule
- HRA calculation
- 7th CPC increment by the current Pay Level's next matrix cell
- Old/New Pay Level handling
- single arrear start/effective date
- old increment Yes/No and missed increment dates
- GPF/RGHS/SI slab calculations
- non-negative deduction differences
- monthly prorating and reconciliation

Important: replace only the existing app.py with this app.py and place arrear_calculation.py in the same folder. Do not delete or replace the existing output/master data files.
