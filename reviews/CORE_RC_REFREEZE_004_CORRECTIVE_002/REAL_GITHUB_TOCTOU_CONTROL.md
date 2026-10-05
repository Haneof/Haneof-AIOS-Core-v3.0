# Real GitHub TOCTOU GREEN control

Canonical late-race control on the actual Corrective-002 branch:

A = 7fa74d5a3a979bc5021978c3e8a85b2b5e3296db
old run = 37267746540

Before drift:
- Job A formal gate SUCCESS
- publisher SUCCESS
- publisher pre-check matched A
- provisional pin HTTP 201
- provisional comment id 203438044
- publisher post-check matched A
- final-seal pre-check SUCCESS
- cancellation propagation guard started

The branch then advanced during the guard:
B = ae0ec67fc1c5fe798f51968b322b22bfabdbd782

Old A outcome:
- FINAL_SEAL_REMOTE_HEAD_MISMATCH remote=B event=A
- whole-run identity seal FAILURE
- old overall run CANCELLED
- old overall != SUCCESS
- its provisional pin is non-authoritative because final seal and overall SUCCESS are absent

Successor B run 37268221493:
- Job A SUCCESS
- publisher SUCCESS
- whole-run identity seal SUCCESS
- overall SUCCESS

Additional publisher-race control:
- A c223d9bf8ec0edb130011902bd5e273aa6f4dcbe
- B 4db5841fe734a425e0e08429dec4d4f5477cd819
- old run 37289807023 CANCELLED
- old publisher CANCELLED
- mock publication SKIPPED
- successor run 37289888964 SUCCESS
