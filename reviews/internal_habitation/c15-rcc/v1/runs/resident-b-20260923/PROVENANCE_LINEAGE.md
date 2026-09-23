# C15-RCC-RES-B-001 Provenance Lineage

> Task: C15-RCC-RES-B-001  
> Resident: Fresh AI instance (Resident B)  

## 1. Durable World Lineage

### 1.1 Phase A → Phase B Handoff

```
Phase A (Resident A)
├── Session: resident-a-final-rerun-20260923-001
├── Cursors: 1-13
├── World Revision: 88
├── Claims: 3 (User Understanding, Relationship, Strategy)
├── Experiences: 2 (Communication, Operation)
├── Observations: 20
└── Handoff State: release_state.json (next_sequence=14)
    ↓
Phase B (Resident B)
├── Session: resident-b-c15-rcc-20260923-001
├── Cursors: 14-22
├── World Revision: 97
├── Claims: 0 new (inherited 3 from Phase A)
├── Observations: 9 new (total 29)
└── State: release_state.json (next_sequence=23)
```

### 1.2 World Object Lineage

**Phase A Objects (inherited):**
- 20 observations (14 conversation + 6 platform)
- 3 claims (user_understanding, relationship, strategy)
- 2 experiences (communication, operation)
- 11 evidence sets
- 89 dependencies
- 22 summaries
- 51 wakes

**Phase B Objects (created):**
- 9 observations (4 user conversation + 5 platform)
- 0 new claims (used existing)
- 0 new experiences (used existing)
- 0 new evidence sets
- 0 new dependencies
- 0 new summaries
- 0 new wakes

## 2. Claim Provenance

### 2.1 User Understanding Claim

```
clm_d95e2508b26a0292b94a7a59
├── Created: 2026-11-02T17:05 (Phase A, wr=2)
├── Revisions: 5 (rev1→rev5)
├── Latest: 2026-11-04T22:24 (Phase A, wr=59)
├── Evidence Chain:
│   ├── evs_b8fc48039bb81ac73c7d6215@1 (3 pinned leaves)
│   ├── evs_revision_c54e57c7167554cdbc99be3c@1 (6 pinned leaves)
│   ├── evs_revision_18008a10aeb60acc83d9b185@1 (6 pinned leaves)
│   └── evs_revision_4b95af9344a7de0e334e0d86@1 (12 pinned leaves)
├── Source Observations:
│   ├── obs_conv_user_5a96a6b7f95ebb907cc8f292@1 (user delegation)
│   ├── obs_conv_user_00157f98462d7a1d7ff1a34a@1 (testing boundary)
│   ├── obs_conv_user_83b5da89c5b5751f2503919f@1 (positive feedback)
│   ├── obs_conv_user_2c65e6bb5864bd57d4f0432f@1 (deletion boundary)
│   ├── obs_conv_user_88047ce5294340f597841c38@1 (status reporting)
│   └── obs_c14_fixture_* (platform events)
└── Domain: user_understanding
```

### 2.2 Relationship Claim

```
clm_776c4bbfaab7540a23c418cb
├── Created: 2026-11-02T17:05 (Phase A, wr=3)
├── Revisions: 3 (rev1→rev3)
├── Latest: 2026-11-02T20:52 (Phase A, wr=13)
├── Evidence Chain:
│   ├── evs_fc47717450d1548d19fbd2b0@1
│   ├── evs_revision_8242fa9d0162cdef3d16acff@1
│   └── evs_revision_618045313f7bc5174f2009b7@1
└── Domain: relationship
```

### 2.3 Strategy Claim

```
clm_52276ec49967d10c72861d07
├── Created: 2026-11-02T20:52 (Phase A, wr=14)
├── Revisions: 3 (rev1→rev3)
├── Latest: 2026-11-04T22:24 (Phase A, wr=60)
├── Evidence Chain:
│   ├── evs_ff6e750c5628bdfd53949569@1
│   └── evs_revision_793bcf22b103652a70ca4d00@1
└── Domain: strategy
```

## 3. Experience Provenance

### 3.1 Communication Experience

```
commexp_f3778968f998cd698281e0ee
├── Created: 2026-11-02T20:52 (Phase A, wr=15)
├── Evidence:
│   ├── obs_c14_fixture_5d4dfcf42055c00135a78a54@1 (staging completion)
│   └── obs_conv_user_83b5da89c5b5751f2503919f@1 (user feedback)
└── Learning: Report results + key risks for low-risk work
```

### 3.2 Operation Experience

```
opexp_4c982ed6ba398f2a8404e4d0
├── Created: 2026-11-05T17:05 (Phase A, wr=72)
├── Evidence: Platform records (completion events, tags, digests)
└── Learning: Status reporting - platform records as source of truth
```

## 4. Phase B Event Provenance

### 4.1 Event → Observation Mapping

| Event | Observation ID | Source Class | WR | Description |
|-------|---------------|--------------|-----|-------------|
| c15rcc-014 | obs_c14_fixture_4c492ea152d135960e96c2d1 | platform | 89 | Staging index conflict |
| c15rcc-015 | obs_conv_user_78892f420536208b2a79026a | user | 90 | "Handle staging conflict before regression" |
| c15rcc-016 | obs_c14_fixture_27950c95292547c4b359cc57 | platform | 91 | Staging conflict resolved |
| c15rcc-017 | obs_conv_user_c74bceeff473073582577ed9 | user | 92 | "Clean up old production index" |
| c15rcc-018 | obs_c14_fixture_3fd30a3cca0f01f839fc0c46 | platform | 93 | Audit system needs index tomorrow |
| c15rcc-019 | obs_conv_user_e21d44093c25f6927bb83fda | user | 94 | "Don't delete yet, list impact first" |
| c15rcc-020 | obs_c14_fixture_b6d15e908fa07010154b86e0 | platform | 95 | Third-party 503 outage |
| c15rcc-021 | obs_c14_fixture_136e77a80d198d7d83dbff23 | platform | 96 | Integration failed then retried |
| c15rcc-022 | obs_conv_user_7d96f8cc54e3691af0e913c0 | user | 97 | "Lunch choice - you decide" |

### 4.2 Fixture Binding

All Phase B observations are bound to:
- Fixture version: `c15-rcc-fixture-v1`
- Fixture SHA256: `sha256:7ccb309d207cb6ee240fbc008ee4f535e25571f04ba7ca1b7c95bf9afb5ebf46`
- Binding version: `c15-rcc-fixture-event-binding-v1` (mechanical) / `c15-rcc-canonical-conversation-binding-v1` (canonical)

## 5. Cross-Phase Continuity

### 5.1 Cognition Consumption Chain

```
Phase A Cognition Formation
├── User Understanding: rev1→rev5
├── Relationship: rev1→rev3
├── Strategy: rev1→rev3
├── Communication Experience: rev1
└── Operation Experience: rev1
    ↓
Phase B Cognition Consumption
├── Cursor 14: Staging conflict → Used strategy (handle autonomously)
├── Cursor 15: User delegation → Validated relationship (autonomous role)
├── Cursor 16: Resolution → Validated strategy (report results)
├── Cursor 17: Deletion request → Used user_understanding (require confirmation)
├── Cursor 18: Audit needs → UNKNOWN (external dependency)
├── Cursor 19: User clarification → Validated user_understanding (boundary confirmed)
├── Cursor 20: External failure → Used operation_experience (no self-blame)
├── Cursor 21: Retry success → Validated operation_experience (platform truth)
└── Cursor 22: Lunch choice → UNKNOWN (non-technical domain)
```

### 5.2 No Cognition Reset

Between Phase A and Phase B:
- ✓ All claims remained in World
- ✓ All experiences remained in World
- ✓ All evidence sets remained in World
- ✓ All dependencies remained in World
- ✓ No cognition was deleted or overwritten
- ✓ New session did NOT reset any cognition

## 6. Lineage Integrity

### 6.1 Forward-Only Revisions

All claim revisions are forward-only:
- `clm_d95e2508b26a0292b94a7a59`: rev1→rev2→rev3→rev4→rev5
- `clm_776c4bbfaab7540a23c418cb`: rev1→rev2→rev3
- `clm_52276ec49967d10c72861d07`: rev1→rev2→rev3

No backward revisions, no revision deletion.

### 6.2 Evidence Grounding

Every claim revision has:
- ✓ At least one pinned evidence set
- ✓ Evidence sets contain real observations
- ✓ No synthetic or AI-generated evidence
- ✓ No summary-only evidence chains

### 6.3 Durable Storage

All provenance data is:
- ✓ Stored in SQLite World
- ✓ Survives process restart
- ✓ Recoverable through normal AIOS capabilities
- ✓ Not dependent on chat context or transcripts
