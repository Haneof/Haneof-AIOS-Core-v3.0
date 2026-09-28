# AIOS Cognition Scale Benchmark Report (C15-RCC-SCALE-BENCH-001)

- **Date**: 2026-09-22
- **Role**: AIOS Performance Engineer
- **Target Task**: `C15-RCC-SCALE-BENCH-001`
- **Status**: Completed (Measurement & Scalability Risk Audit)
- **Constraint Compliance**: Zero modifications to Core runtime, database schema, index structures, or retrieval algorithms. Pure observation, measurement, and bottleneck characterization.

---

## Executive Summary

This report establishes the first empirical performance and scale characterization for the AIOS AI-World cognition retrieval subsystem under the C15 roadmap (`governance/C15_RCC_COGNITION_HARDENING_ROADMAP_2026-09-22.md`).

Key findings include:
1. **Performance Boundary at Scale**:
   - At **10,000 Claims**, cognition retrieval operations (`core_context`, `snapshot`, `recall_candidates`) remain well within interactive budgets (< 1 second).
   - At **100,000 Claims**, query latency degrades by an order of magnitude (latencies increase 10x–13x, reaching ~4.4s for `core_context` and ~10.4s for `snapshot`), while `recall_candidates` exhibits severe query amplification executing **37,505 discrete SQL statements** for a single search invocation.
   - At **1,000,000 Claims**, cognition projection cannot complete within the standard 3.8GB memory envelope, triggering the Linux kernel **OOM-Killer**.
2. **Scalability Risk, Not Correctness Blocker**:
   - The functional correctness and cognitive invariants verified across Task 1 (`C15-RCC-EVIDENCE-POLICY-001`) and Task 2 (`C15-RCC-COGNITION-FIELDS-001`) remain intact: no self-confirming loop (`Claim -> Summary -> Claim`), evidence policy enforcement holds, and temporal extent/unknowns are cleanly projected.
   - The failure mode at $10^6$ objects is strictly a **scalability and memory-budget boundary** arising from unindexed full-table scans and Python-side deserialization, rather than a logical defect.

---

## Benchmark Environment

- **Target Repository**: `Haneof/Haneof-AIOS-Core-v3.0`
- **Base Commit (main SHA)**: `e534378572e886f76071ac0dcf59a9a1a4798bb9`
- **Branch**: `arena/01a0c9a2-haneof-aios-core-v3-0`
- **OS & Kernel**: Linux 6.1.158+ x86_64 (Debian GNU/Linux container)
- **Python Version**: `3.11.2`
- **SQLite Version**: `3.40.1` (WAL mode enabled)
- **Physical Memory Limit**: `3.8 GiB` RAM, `0 B` Swap (`cgroup` constrained)

---

## Benchmark Result

All tests were conducted on real isolated SQLite stores populated with realistic multi-domain claims (`user_understanding`, `relationship`, `self`, `intent`, `strategy`, `cognitive_boundary`, `personality`, `calibration`) asserting facts, preferences, inferences, temporal extents, and evidence references.

### 1. Scale: 10,000 Claim

- **Database Size on Disk**: ~25.48 MB
- **`core_context`**:
  - Latency: **~325 ms** (average across runs; min 313 ms, max 357 ms)
  - SQL Execution Count: **3 SQL**
  - Token Count: **~1,023 tokens** (estimated via `estimate_tokens`)
- **`snapshot`**:
  - Latency: **~831 ms** (average across runs)
  - P95 Latency: **~870 ms**
  - SQL Execution Count: **8 SQL**
  - Domain Scan Count: **8 domains**
- **`recall_candidates`**:
  - Latency: **~432 ms** (average across test queries)
  - Candidates Returned: **20 hits** (limit 20)
  - SQL Execution Count: **3,755 SQL**

### 2. Scale: 100,000 Claim

- **Database Size on Disk**: ~254.83 MB
- **`core_context`**:
  - Latency: **~4,445 ms** (min 3,388 ms, max 6,043 ms)
  - SQL Execution Count: **3 SQL**
  - Token Count: **~1,023 tokens**
- **`snapshot`**:
  - Latency: **~10,389 ms** (min 9,524 ms, max 11,875 ms)
  - P95 Latency: **~11,875 ms**
  - SQL Execution Count: **8 SQL**
  - Domain Scan Count: **8 domains**
- **`recall_candidates`**:
  - Latency: **~4,296 ms** (min 3,238 ms, max 6,388 ms)
  - Candidates Returned: **20 hits**
  - SQL Execution Count: **37,505 SQL**

### 3. Scale: 1,000,000 Claim

- **Database Size on Disk (Estimated Raw Table)**: ~783 MB
- **Execution Result**: **Terminated by OS (OOM-Killer)**
- **System Memory Limit**: **3.8 GiB RAM** (0 swap)
- **Failure Cause Analysis**:
  - Building the durable revisions and raw store succeeds in linear time with low transient footprint (~40 MB RSS).
  - During `current()` / `list_payloads(object_type=ObjectType.CLAIM)`, the driver executes `SELECT o.payload_json FROM object_revisions o ...` and loads all $10^6$ JSON payload strings simultaneously into Python process memory (`fetchall()`).
  - At 500,000 claims, `list_payloads()` consumes **2,360 MB RSS**.
  - At 1,000,000 claims, deserializing $10^6$ Python dicts exceeds the container's 3.8 GiB memory ceiling (`anon-rss: 3,878,124 kB`), resulting in `oom-kill: task=python3`.

---

## Root Cause Analysis

Analysis grounded directly in source code implementations:

### 1. `AIWorldCognitionService.current()`: Unfiltered Full-Table Extraction & Memory Inflation
- **Source**: `src/aios_core/ai_world/cognition.py:225` and `src/aios_core/storage/sqlite_store.py:1205-1225`
  ```python
  # src/aios_core/ai_world/cognition.py
  for payload in self.store.list_payloads(object_type=ObjectType.CLAIM):
      metadata = payload.get("metadata")
      if not isinstance(metadata, dict) or not metadata.get("ai_world"):
          continue
      ...
  ```
- **Mechanism**:
  - `list_payloads()` runs a full join over the `object_revisions` table (`JOIN (SELECT object_id, MAX(revision)...)`), fetching every claim's full JSON string.
  - All filtering (by `ai_domain`, by `subject_id`, by `tags`, by `status`, and by `limit`) happens entirely **inside Python** after deserializing all claims.
  - As Claim volume grows to $10^6$, loading and parsing hundreds of megabytes of JSON causes instantaneous memory allocation spikes exceeding 3.8GB.

### 2. `snapshot()`: Domain Loop Multiplicative Scanning
- **Source**: `src/aios_core/ai_world/cognition.py:360-366`
  ```python
  snapshot: dict[str, list[dict[str, Any]]] = {}
  for domain in AIWorldDomain:
      items = self.current(domains=[domain], limit=per_domain)
      if items:
          snapshot[domain.value] = [...]
  ```
- **Mechanism**:
  - There are 8 standard `AIWorldDomain` values. `snapshot()` iterates through each domain sequentially, executing `self.current(domains=[domain])` independently for each one.
  - Because `current()` does not push domain filtering to the database, `snapshot()` triggers **8 complete full-table scans and deserialization passes** over the entire Claim corpus in a single operation.

### 3. `core_context()`: Full-Table Dependency for Low-Cardinality Context
- **Source**: `src/aios_core/ai_world/cognition.py:340-349`
  ```python
  for domain in (
      AIWorldDomain.USER_UNDERSTANDING,
      AIWorldDomain.RELATIONSHIP,
      AIWorldDomain.SELF,
  ):
      selected = self.current(
          domains=[domain],
          required_tags=("core_context",),
          limit=per_domain,
      )
  ```
- **Mechanism**:
  - `core_context` is intended to provide immediate, low-latency grounding for every turn runtime invocation.
  - Despite only needing at most 3 items for 3 domains (total ~6-9 claims, ~1,023 tokens), it invokes `current()` 3 times, scanning and deserializing all $C$ claims 3 times consecutively.

### 4. `recall_candidates()`: Per-Candidate N+1 Query Cascade
- **Source**: `src/aios_core/query/search.py:1120-1165`
  ```python
  for (object_id, revision), score in hits_map.items():
      row = conn.execute(
          "SELECT ... FROM search_occurred o JOIN search_doc d ... WHERE o.object_id=? AND o.revision=?",
          (object_id, revision),
      ).fetchone()
      latest = conn.execute(
          "SELECT MAX(revision) FROM search_occurred WHERE object_id=?",
          (object_id,),
      ).fetchone()
      if not include_inactive and not self._visible_in_current_view(...):
          ...
  ```
- **Mechanism**:
  - When a lexical query matches broad tokens in the inverted index, `hits_map` yields thousands of candidate postings.
  - The loop issues multiple individual SQL queries (`SELECT occurred`, `SELECT MAX(revision)`, plus internal checks) for **every candidate hit** before applying filtering, sorting, or pagination (`limit=20`).
  - At 100,000 claims, this pattern generated **37,505 round-trip database queries** within a single search call.

---

## Complexity Analysis

The asymptotic behavior of the current retrieval architecture is formally characterized as follows:

- **$C$**: Total number of Claims in the World Store.
- **$D$**: Number of target domains ($D = 8$ for `snapshot`, $D = 3$ for `core_context`).
- **$H$**: Number of candidate hits returned from inverted postings for a query.
- **$Q$**: Number of distinct database queries executed per candidate hit ($Q \ge 2$).

### Rigorous Formulations:

1. **`core_context` Complexity: $\mathcal{O}(C)$**
   $$\mathcal{T}_{\text{core\_context}} = 3 \times \mathcal{O}(C) = \mathcal{O}(C)$$
   - Space Complexity: $\mathcal{O}(C)$ memory allocation per call due to full-table `fetchall()`.
   - Latency scales strictly linearly with total world size rather than active context size.

2. **`snapshot` Complexity: $\mathcal{O}(D \times C)$**
   $$\mathcal{T}_{\text{snapshot}} = D \times \mathcal{O}(C) = \mathcal{O}(D \times C)$$
   - Each domain triggers a discrete full-table sweep.
   - For 8 domains at 100k claims, $8 \times 10^5$ claim payloads are serialized across the boundary.

3. **`recall_candidates` Complexity: $\mathcal{O}(H \times Q)$**
   $$\mathcal{T}_{\text{recall\_candidates}} = \mathcal{O}(\text{postings\_lookup}) + \mathcal{O}(H \times Q) + \mathcal{O}(H \log H)$$
   - Dominated by $\mathcal{O}(H \times Q)$ database round-trips.
   - As the corpus grows, frequent search terms match an increasing number of postings ($H$), causing the $N+1$ query overhead to dominate query time over inverted index retrieval.

---

## Future Optimization Direction

*(Architectural roadmap and non-invasive design guidance for subsequent engineering phases. In strict accordance with the constraints of Task `C15-RCC-SCALE-BENCH-001`, **none** of these changes are implemented in this change set; Core runtime, database schema, index structures, and retrieval algorithms remain strictly unmodified.)*

### Level 1: Non-Schema Driver Optimizations
- **Filter Pushdown**:
  - Leverage SQLite `json_extract(payload_json, '$.metadata.ai_domain')` or dedicated column clauses to filter domains and tags directly in SQL before returning rows.
- **Batch Querying & Elimination of N+1**:
  - Replace candidate iteration in `recall_candidates()` with batch `IN (?, ?, ...)` queries or temporary staging tables, reducing $H \times Q$ queries down to a constant number of queries ($\mathcal{O}(1)$ query round-trips).
- **Lazy Streaming & Generator Deserialization**:
  - Replace `fetchall()` with cursor streaming (`fetchmany()` / generators) with early termination once the required domain `limit` is satisfied.

### Level 2: Projections & Index Hardening
- **Cognition Materialized Projections**:
  - Maintain a lightweight projection table `ai_cognition_view` populated asynchronously during commit watermarking, indexing `(domain, subject_id, status)` and tag membership.
- **Composite Index Coverage**:
  - Introduce covered indexes on `search_occurred (object_id, revision, dimension)` to satisfy latest-revision checks in a single index lookup.

### Level 3: Large-Scale Semantic & Sharded Retrieval
- **Hierarchical Domain Partitioning**:
  - Segment cognition retrieval by domain namespace or temporal partitions for long-horizon resident histories exceeding $10^7$ events.
- **Vector / Approximate Retrieval Handoff**:
  - Offload high-cardinality candidate generation to dedicated vector/lexical engines while preserving Core's deterministic SQLite truth store as the authoritative verification plane.

---

## Governance & Compliance Statement

- **Core Preservation**: Zero Core runtime logic, data schemas, or retrieval contracts were altered.
- **Fixtures & Boundaries**: No resident fixtures, life fixtures, or constitutional invariants were touched.
- **Verification**: Report grounded in reproducible empirical executions on commit `e534378`.
