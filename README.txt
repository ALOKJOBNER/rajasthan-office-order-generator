Revised arrear_calculation.py

Only arrear calculation engine is included.
Fixes in this version:
1. Restores get_initial_due_basic compatibility for app.py imports.
2. calculate_arrear accepts initial_due_fixation_applied compatibility argument.
3. January-selected increment is applied from 1 January.
4. July-selected increment is applied from 1 July.
5. Due and Drawn increments are applied before calculating that month's row.
6. Promotion automatic fixation helper remains: old-level increment, then strictly higher cell in new level.
No app.py or PDF-layout code is included/changed.
