# RED-first TOCTOU reproduction

Window 27 hosted control was freshly re-verified:
- run 37262331480
- event SHA A 4fb32d9b94a79e342af770050d71a45a24677008
- branch later advanced to e4fd46c04c8ad982fa1fa274546dbf0d099343c5
- old gate SUCCESS
- old publisher SUCCESS
- old overall SUCCESS

Window 28 independently reproduced RED before relying on the corrected lifecycle:
- branch control/w28-toctou-red-window28
- A 60e53408729efdb29f08c0c2063b37d34fea1f09
- old run 37289298552
- terminal remote-head equality SUCCESS
- branch then advanced to B dabf9c98d0736869ec95e7d0a34ebbe42213e3ee
- old gate SUCCESS
- old publisher SUCCESS
- old overall SUCCESS
- successor B run 37289340609 was created

RED_TOCTOU_REPRODUCED=YES
