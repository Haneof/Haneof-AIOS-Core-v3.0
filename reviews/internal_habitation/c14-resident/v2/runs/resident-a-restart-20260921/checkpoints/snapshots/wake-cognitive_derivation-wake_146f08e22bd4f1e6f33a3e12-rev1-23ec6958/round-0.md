# RuntimeSnapshot — wake-cognitive_derivation-wake_146f08e22bd4f1e6f33a3e12-rev1

- round_index: 0
- remaining_tool_rounds: 4
- wake_reason: cognitive_derivation

## wake_input

```text
Cognitive derivation bundle wake. The listed pinned Summaries are independent temporal/navigation anchors, not Claims or conclusions. Inspect whichever member leaves, existing cognition, counter-evidence, and cross-dimensional world state you judge relevant. Only form, revise, or retract durable cognition when pinned support closes to qualifying non-Summary reality/case evidence. Silence is a valid successful result. Mechanical bundling makes no semantic claim about the members.
```

## cockpit

```json
{
  "ai_identity": {},
  "capability_catalog": [
    {
      "description": "Persist a typed AI-world cognition using the unified EvidenceSet + Claim + Dependency path.",
      "hard_boundary": false,
      "input_schema": {
        "claim_type": "string?",
        "confidence": "number[0,1]",
        "domain": "user_understanding|relationship|self|intent|strategy|cognitive_boundary|personality|calibration",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "knowledge_state": "string?",
        "scope_key": "string?",
        "statement": "string",
        "tags": "array[string]?"
      },
      "kind": "write",
      "name": "commit_ai_world_claim",
      "side_effecting": true
    },
    {
      "description": "Persist a revisable AI cognition Claim grounded in pinned world evidence. This capability cannot create Observation facts.",
      "hard_boundary": false,
      "input_schema": {
        "claim_type": "string?",
        "confidence": "number[0,1]",
        "content": "string",
        "dimension": "string",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "knowledge_state": "string?"
      },
      "kind": "write",
      "name": "commit_claim",
      "side_effecting": true
    },
    {
      "description": "During an active periodic review, persist a model-authored operation experience grounded in pinned real case refs.",
      "hard_boundary": false,
      "input_schema": {
        "applicability": "object?",
        "cost": "object[number]?",
        "experience_state": "string?",
        "method_path": "array[string]",
        "misses": "array[string]?",
        "negative_case_refs": "array[{object_id:string,revision:integer}]?",
        "positive_case_refs": "array[{object_id:string,revision:integer}]?",
        "problem_type": "string",
        "result_summary": "string"
      },
      "kind": "write",
      "name": "commit_operation_experience",
      "side_effecting": true
    },
    {
      "description": "Inspect multiple pinned Claims side by side with their evidence/status; the model decides meaning.",
      "hard_boundary": false,
      "input_schema": {
        "claim_refs": "array[{object_id:string,revision:integer}]"
      },
      "kind": "read",
      "name": "compare_claims",
      "side_effecting": false
    },
    {
      "description": "Register future attention as a constrained mechanical Observation watch. The Resident chooses the routing class: interrupt wakes cognition immediately and may allow user delivery after Resident judgment; background waits for short mechanical batching, invokes cognition, and is silent to the user by default; review_queue does not invoke the Resident immediately and carries matched evidence into Periodic Review. Choose the class from the future-attention intent and current runtime facts; Core does not infer urgency for you. Do not encode emotion, intent, diagnosis, or other semantic conclusions in the mechanical predicate.",
      "hard_boundary": false,
      "input_schema": {
        "attention_class": "interrupt|background|review_queue?",
        "cooldown_seconds": "integer?",
        "dimensions": "array[string]",
        "expires_at": "ISO-8601 datetime?",
        "goal_ref": "{object_id:string,revision:integer}?",
        "metadata_equals": "object?",
        "modality": "string?",
        "mode": "recurring|one_shot?",
        "numeric": "{operator:gt|gte|lt|lte|eq|ne,threshold:number,path:array[string]?}?",
        "priority": "integer?",
        "reason_refs": "array[{object_id:string,revision:integer}]",
        "source_kind": "string?",
        "title": "string"
      },
      "kind": "write",
      "name": "create_attention_watch",
      "side_effecting": true
    },
    {
      "description": "Create a concrete evidence-grounded Task, optionally under a current Goal.",
      "hard_boundary": false,
      "input_schema": {
        "completion_condition": "object?; use mode=world_evidence|action_outcome|mixed; optional result_object_types=array[string]",
        "deadline": "ISO-8601 datetime?",
        "goal_ref": "{object_id:string,revision:integer}?",
        "initial_state": "string?",
        "next_step": "string?",
        "next_wake_at": "ISO-8601 datetime?",
        "priority": "integer?",
        "reason_refs": "array[{object_id:string,revision:integer}]",
        "task_type": "string",
        "timezone_name": "string?",
        "title": "string"
      },
      "kind": "write",
      "name": "create_task",
      "side_effecting": true
    },
    {
      "description": "Read exact pinned raw dialogue behind a same-session round summary, or an explicit turn range. Round summaries are indexes, not truth.",
      "hard_boundary": false,
      "input_schema": {
        "revision": "integer?",
        "session_id": "string?",
        "summary_id": "string?",
        "turn_end": "integer?",
        "turn_start": "integer?"
      },
      "kind": "read",
      "name": "drill_down_conversation",
      "side_effecting": false
    },
    {
      "description": "Request a broader bounded world recall after the initial recommendation/search was insufficient.",
      "hard_boundary": false,
      "input_schema": {
        "dimension": "string?",
        "limit": "integer?",
        "query": "string"
      },
      "kind": "read",
      "name": "expand_recall",
      "side_effecting": false
    },
    {
      "description": "Focus retrieval on one known Entity id without semantic reinterpretation.",
      "hard_boundary": false,
      "input_schema": {
        "entity_id": "string",
        "limit": "integer?",
        "query": "string?"
      },
      "kind": "read",
      "name": "focus_entity",
      "side_effecting": false
    },
    {
      "description": "Follow one-hop explicit Relation objects connected to a world object.",
      "hard_boundary": false,
      "input_schema": {
        "limit": "integer?",
        "object_id": "string"
      },
      "kind": "read",
      "name": "follow_relation",
      "side_effecting": false
    },
    {
      "description": "Form a revisable Event candidate from pinned world evidence. The model supplies the event meaning; code only validates provenance.",
      "hard_boundary": false,
      "input_schema": {
        "confidence": "number[0,1]",
        "dimension": "string?",
        "event_time": "TemporalExtent object",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "interpretation": "string",
        "participant_refs": "array[{object_id:string,revision:integer}]?",
        "primary_claim_refs": "array[{object_id:string,revision:integer}]?",
        "title": "string"
      },
      "kind": "write",
      "name": "form_event",
      "side_effecting": true
    },
    {
      "description": "Inspect a pinned real Action Outcome and its Action reference.",
      "hard_boundary": false,
      "input_schema": {
        "outcome_ref": "{object_id:string,revision:integer}"
      },
      "kind": "read",
      "name": "inspect_outcome",
      "side_effecting": false
    },
    {
      "description": "Read one pinned or latest world object by object id.",
      "hard_boundary": false,
      "input_schema": {
        "object_id": "string",
        "revision": "integer?"
      },
      "kind": "read",
      "name": "inspect_world_object",
      "side_effecting": false
    },
    {
      "description": "List Resident-authored active attention watches. Watches contain only mechanical future-match predicates; the Resident interprets meaning after Wake.",
      "hard_boundary": false,
      "input_schema": {},
      "kind": "read",
      "name": "list_attention_watches",
      "side_effecting": false
    },
    {
      "description": "List same-session continuity summary windows on demand. Use this when token budgeting omitted summary content from the cockpit.",
      "hard_boundary": false,
      "input_schema": {
        "limit": "integer?",
        "session_id": "string?"
      },
      "kind": "read",
      "name": "list_conversation_summaries",
      "side_effecting": false
    },
    {
      "description": "List current registered dimension definitions so the resident AI can check whether an existing observation axis already serves the need.",
      "hard_boundary": false,
      "input_schema": {
        "include_terminal": "boolean?"
      },
      "kind": "read",
      "name": "list_dimensions",
      "side_effecting": false
    },
    {
      "description": "Create a PROPOSED external Action for a RUNNING Task. This capability never executes the side effect and cannot authorize itself.",
      "hard_boundary": false,
      "input_schema": {
        "action_type": "string",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "expected_outcome": "string?",
        "payload": "object",
        "task_ref": "{object_id:string,revision:integer}"
      },
      "kind": "write",
      "name": "propose_action",
      "side_effecting": true
    },
    {
      "description": "Register a new evidence-grounded AI-mutable cognitive policy. Only real user/world result evidence is accepted; hard boundaries cannot be created by the resident AI.",
      "hard_boundary": false,
      "input_schema": {
        "allowed_range_or_choices": "json value?",
        "current_value": "json value",
        "default_value": "json value",
        "evaluation_window": "string",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "policy_id": "string",
        "reason": "string",
        "scope": "string"
      },
      "kind": "write",
      "name": "propose_cognitive_policy",
      "side_effecting": true
    },
    {
      "description": "Submit an evidence-grounded candidate observation axis. The system validates structure; the model supplies semantic rationale.",
      "hard_boundary": false,
      "input_schema": {
        "confidence": "number[0,1]",
        "continuity_rationale": "string",
        "data_shape": "string",
        "description": "string",
        "dimension_key": "string starting dim:",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "expected_value": "string?",
        "maintenance_cost_rationale": "string",
        "name": "string",
        "update_method": "string?",
        "user_value_rationale": "string",
        "why_existing_dimensions_are_insufficient": "string"
      },
      "kind": "write",
      "name": "propose_dimension",
      "side_effecting": true
    },
    {
      "description": "Create a durable Entity anchor from pinned same-world evidence. The resident supplies identity meaning; Core enforces explicit entity_key and provenance.",
      "hard_boundary": false,
      "input_schema": {
        "aliases": "array[string]?",
        "canonical_name": "string?",
        "entity_key": "string",
        "entity_kind": "string",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "identity_claim_refs": "array[{object_id:string,revision:integer}]?"
      },
      "kind": "write",
      "name": "propose_entity",
      "side_effecting": true
    },
    {
      "description": "Create an evidence-grounded Goal proposal in the unified world. A proposal does not grant external-action authorization.",
      "hard_boundary": false,
      "input_schema": {
        "confidence": "number[0,1]",
        "description": "string",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "source_type": "user_explicit|user_inferred|ai_self|app|external",
        "success_criteria": "array[string]?",
        "title": "string"
      },
      "kind": "write",
      "name": "propose_goal",
      "side_effecting": true
    },
    {
      "description": "Read current evidence-grounded AI cognition across user understanding, relationship, self, intent, strategy, boundary, personality and calibration.",
      "hard_boundary": false,
      "input_schema": {
        "domains": "array[string]?",
        "limit": "integer?",
        "scope_key": "string?"
      },
      "kind": "read",
      "name": "read_ai_world",
      "side_effecting": false
    },
    {
      "description": "Read the current mechanical BACKGROUND_DAY budget and durable usage. This reports policy caps, Wake/model-call usage and remaining capacity only; it does not decide which future fact is important.",
      "hard_boundary": false,
      "input_schema": {},
      "kind": "read",
      "name": "read_background_budget",
      "side_effecting": false
    },
    {
      "description": "Read current versioned R6 policy records from the unified world.",
      "hard_boundary": false,
      "input_schema": {
        "policy_id": "string?"
      },
      "kind": "read",
      "name": "read_cognitive_policies",
      "side_effecting": false
    },
    {
      "description": "Read current Goals, Tasks and proposed/executed Actions from the unified world. This is a read-only planning view.",
      "hard_boundary": false,
      "input_schema": {},
      "kind": "read",
      "name": "read_execution_world",
      "side_effecting": false
    },
    {
      "description": "Read a bounded page of the evidence anchors selected for the currently active periodic review. Available only during review.",
      "hard_boundary": false,
      "input_schema": {
        "limit": "integer?",
        "offset": "integer?"
      },
      "kind": "read",
      "name": "read_periodic_review_anchors",
      "side_effecting": false
    },
    {
      "description": "Refresh the compact L0 world-map directory. Returns dimension identity, mechanical activity/count metadata and expansion capability names only; it does not return dimension payloads or semantic conclusions.",
      "hard_boundary": false,
      "input_schema": {},
      "kind": "read",
      "name": "read_world_map",
      "side_effecting": false
    },
    {
      "description": "Record what communication style was used and the real user/world reaction. This records evidence only and does not choose a future style.",
      "hard_boundary": false,
      "input_schema": {
        "action_ref": "{object_id:string,revision:integer}?",
        "applicable_conditions": "object?",
        "counterexample_refs": "array[{object_id:string,revision:integer}]?",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "scenario": "string",
        "style": "string",
        "tone": "string?",
        "user_reaction": "accepted|resisted|ignored|unknown"
      },
      "kind": "write",
      "name": "record_communication_experience",
      "side_effecting": true
    },
    {
      "description": "Observe several parallel dimensions in one time window without turning co-occurrence into a causal conclusion.",
      "hard_boundary": false,
      "input_schema": {
        "dimensions": "array[string]",
        "query": "string?",
        "window_end": "ISO-8601 datetime",
        "window_start": "ISO-8601 datetime"
      },
      "kind": "read",
      "name": "request_all_dimensions_projection",
      "side_effecting": false
    },
    {
      "description": "Retract the current Claim using pinned contrary/correcting evidence and propagate review-required state to dependents.",
      "hard_boundary": false,
      "input_schema": {
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "reason": "string",
        "target_ref": "{object_id:string,revision:integer}"
      },
      "kind": "write",
      "name": "retract_claim",
      "side_effecting": true
    },
    {
      "description": "Retrieve an exact Observation fact by id/revision for evidence drill-down.",
      "hard_boundary": false,
      "input_schema": {
        "object_id": "string",
        "revision": "integer?"
      },
      "kind": "read",
      "name": "retrieve_original_observation",
      "side_effecting": false
    },
    {
      "description": "Create a forward-only new revision of the current Claim and mark dependent cognition review-required.",
      "hard_boundary": false,
      "input_schema": {
        "confidence": "number[0,1]?",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "reason": "string",
        "replacement_content": "string",
        "target_ref": "{object_id:string,revision:integer}"
      },
      "kind": "write",
      "name": "revise_claim",
      "side_effecting": true
    },
    {
      "description": "Append a new revision of the current Entity identity anchor using pinned evidence.",
      "hard_boundary": false,
      "input_schema": {
        "aliases": "array[string]?",
        "canonical_name": "string?",
        "entity_ref": "{object_id:string,revision:integer}",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "identity_claim_refs": "array[{object_id:string,revision:integer}]?",
        "reason": "string"
      },
      "kind": "write",
      "name": "revise_entity",
      "side_effecting": true
    },
    {
      "description": "Forward-append a rollback to an earlier policy version using pinned evidence.",
      "hard_boundary": false,
      "input_schema": {
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "policy_id": "string",
        "reason": "string",
        "target_version": "integer"
      },
      "kind": "write",
      "name": "rollback_cognitive_policy",
      "side_effecting": true
    },
    {
      "description": "Search same-session round-summary indexes by topic/text, then drill down to exact pinned raw dialogue when precision is needed.",
      "hard_boundary": false,
      "input_schema": {
        "limit": "integer?",
        "query": "string",
        "session_id": "string?"
      },
      "kind": "read",
      "name": "search_conversation_summaries",
      "side_effecting": false
    },
    {
      "description": "Search the world inside an explicit time window, optionally bounded by dimension/type/query.",
      "hard_boundary": false,
      "input_schema": {
        "dimension": "string?",
        "limit": "integer?",
        "object_types": "array[string]?",
        "query": "string?",
        "window_end": "ISO-8601 datetime",
        "window_start": "ISO-8601 datetime"
      },
      "kind": "read",
      "name": "search_timeline",
      "side_effecting": false
    },
    {
      "description": "Recall candidate world objects related to a query.",
      "hard_boundary": false,
      "input_schema": {
        "limit": "integer?",
        "query": "string"
      },
      "kind": "read",
      "name": "search_world",
      "side_effecting": false
    },
    {
      "description": "Move the current dimension revision through a legal lifecycle transition using pinned evidence and an AI-supplied reason.",
      "hard_boundary": false,
      "input_schema": {
        "dimension_ref": "{object_id:string,revision:integer}",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "new_lifecycle": "candidate|trial|active|low_activity|dormant|merged|split|revised|rejected|reactivated|archived",
        "reason": "string",
        "related_dimension_refs": "array[{object_id:string,revision:integer}]?"
      },
      "kind": "write",
      "name": "transition_dimension",
      "side_effecting": true
    },
    {
      "description": "Forward-revise/resolve/reject/merge/split the current Event using pinned evidence.",
      "hard_boundary": false,
      "input_schema": {
        "confidence": "number[0,1]?",
        "event_ref": "{object_id:string,revision:integer}",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "new_status": "candidate|active|resolved|revised|rejected|merged|split",
        "reason": "string",
        "related_event_refs": "array[{object_id:string,revision:integer}]?",
        "replacement_interpretation": "string?",
        "replacement_title": "string?"
      },
      "kind": "write",
      "name": "transition_event",
      "side_effecting": true
    },
    {
      "description": "Move the current Goal revision through a legal evidence-backed state transition.",
      "hard_boundary": false,
      "input_schema": {
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "goal_ref": "{object_id:string,revision:integer}",
        "new_status": "proposed|active|paused|achieved|abandoned|unknown",
        "reason": "string"
      },
      "kind": "write",
      "name": "transition_goal",
      "side_effecting": true
    },
    {
      "description": "Move the current Task revision through a legal state transition. Terminal transitions obey the Task's explicit completion mode: WORLD_EVIDENCE uses pinned durable evidence; ACTION_OUTCOME requires a real authorized Action-linked Outcome; MIXED requires both.",
      "hard_boundary": false,
      "input_schema": {
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "execution_refs": "array[{object_id:string,revision:integer}]?",
        "new_state": "string",
        "next_step": "string?",
        "next_wake_at": "ISO-8601 datetime?",
        "outcome_refs": "array[{object_id:string,revision:integer}]?",
        "reason": "string",
        "task_ref": "{object_id:string,revision:integer}"
      },
      "kind": "write",
      "name": "transition_task",
      "side_effecting": true
    },
    {
      "description": "Append an evidence-grounded value revision to an already-registered AI-mutable cognitive policy. Cannot create or loosen hard boundaries.",
      "hard_boundary": false,
      "input_schema": {
        "current_value": "json value",
        "evaluation_window": "string?",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "policy_id": "string",
        "reason": "string"
      },
      "kind": "write",
      "name": "update_cognitive_policy",
      "side_effecting": true
    },
    {
      "description": "Create or forward-revise an evidence-grounded Relation between current Entity revisions.",
      "hard_boundary": false,
      "input_schema": {
        "confidence": "number[0,1]",
        "evidence_refs": "array[{object_id:string,revision:integer}]",
        "left_ref": "{object_id:string,revision:integer}",
        "reason": "string",
        "relation_type": "string",
        "right_ref": "{object_id:string,revision:integer}",
        "valid_time": "TemporalExtent object?"
      },
      "kind": "write",
      "name": "upsert_relation",
      "side_effecting": true
    }
  ],
  "conversation_summaries": [],
  "current_topic": null,
  "estimated_tokens": 8363,
  "memory_cards": [],
  "recent_turns": [],
  "task_context": {
    "cognitive_derivation_bundle": {
      "budget": {
        "applies": false,
        "available": true,
        "max_model_calls": null,
        "max_wakes": null,
        "model_round_limit": null,
        "policy_refs": [],
        "reasons": [],
        "reserved_model_calls": 0,
        "scope": null,
        "token_usage_available": false,
        "used_model_calls": 0,
        "used_tokens": 0,
        "used_wakes": 0,
        "window_end": null,
        "window_start": null
      },
      "bundle_wake_ref": {
        "object_id": "wake_bundle_71c8cb5b630bcdc3161fa4df",
        "revision": 2
      },
      "capability_names": [
        "commit_ai_world_claim",
        "commit_claim",
        "commit_operation_experience",
        "compare_claims",
        "create_attention_watch",
        "create_task",
        "drill_down_conversation",
        "expand_recall",
        "focus_entity",
        "follow_relation",
        "form_event",
        "inspect_outcome",
        "inspect_world_object",
        "list_attention_watches",
        "list_conversation_summaries",
        "list_dimensions",
        "propose_action",
        "propose_cognitive_policy",
        "propose_dimension",
        "propose_entity",
        "propose_goal",
        "read_ai_world",
        "read_background_budget",
        "read_cognitive_policies",
        "read_execution_world",
        "read_periodic_review_anchors",
        "read_world_map",
        "record_communication_experience",
        "request_all_dimensions_projection",
        "retract_claim",
        "retrieve_original_observation",
        "revise_claim",
        "revise_entity",
        "rollback_cognitive_policy",
        "search_conversation_summaries",
        "search_timeline",
        "search_world",
        "transition_dimension",
        "transition_event",
        "transition_goal",
        "transition_task",
        "update_cognitive_policy",
        "upsert_relation"
      ],
      "current_ai_world": {
        "calibration": [],
        "cognitive_boundary": [],
        "intent": [],
        "personality": [],
        "relationship": [],
        "self": [],
        "strategy": [],
        "user_understanding": []
      },
      "grouping_policy": "homogeneous_execution_contract",
      "member_count": 4,
      "members": [
        {
          "granularity": "day",
          "grounding_leaf_refs": [
            {
              "object_id": "obs_c14_fixture_056dddd04850d813437e8532",
              "revision": 1
            }
          ],
          "runtime_derived_lineage": {
            "classification": "REALITY",
            "grounding_leaf_refs": [
              {
                "object_id": "obs_c14_fixture_056dddd04850d813437e8532",
                "revision": 1
              }
            ],
            "has_ai_cognition": false,
            "has_maintenance": false,
            "has_reality": true,
            "issues": [],
            "leaf_refs": [
              {
                "object_id": "obs_c14_fixture_056dddd04850d813437e8532",
                "revision": 1
              }
            ],
            "unresolved_refs": []
          },
          "scheduler_derived_lineage": {
            "classification": "REALITY",
            "grounding_leaf_refs": [
              {
                "object_id": "obs_c14_fixture_056dddd04850d813437e8532",
                "revision": 1
              }
            ],
            "has_ai_cognition": false,
            "has_maintenance": false,
            "has_reality": true,
            "issues": [],
            "leaf_refs": [
              {
                "object_id": "obs_c14_fixture_056dddd04850d813437e8532",
                "revision": 1
              }
            ],
            "unresolved_refs": []
          },
          "summary_dimension": "dim:sleep",
          "summary_ref": {
            "object_id": "sum_f25eb0e55e8258fb59baf085",
            "revision": 1
          },
          "summary_revision": 1,
          "summary_window": {
            "end": "2026-10-08T23:59:59.999999Z",
            "precision": "day",
            "start": "2026-10-08T00:00:00Z",
            "timezone_name": null,
            "unknown": false
          },
          "wake_ref": {
            "object_id": "wake_146f08e22bd4f1e6f33a3e12",
            "revision": 1
          }
        },
        {
          "granularity": "day",
          "grounding_leaf_refs": [
            {
              "object_id": "obs_c14_fixture_522a6cbeb84ced83b62def58",
              "revision": 1
            }
          ],
          "runtime_derived_lineage": {
            "classification": "REALITY",
            "grounding_leaf_refs": [
              {
                "object_id": "obs_c14_fixture_522a6cbeb84ced83b62def58",
                "revision": 1
              }
            ],
            "has_ai_cognition": false,
            "has_maintenance": false,
            "has_reality": true,
            "issues": [],
            "leaf_refs": [
              {
                "object_id": "obs_c14_fixture_522a6cbeb84ced83b62def58",
                "revision": 1
              }
            ],
            "unresolved_refs": []
          },
          "scheduler_derived_lineage": {
            "classification": "REALITY",
            "grounding_leaf_refs": [
              {
                "object_id": "obs_c14_fixture_522a6cbeb84ced83b62def58",
                "revision": 1
              }
            ],
            "has_ai_cognition": false,
            "has_maintenance": false,
            "has_reality": true,
            "issues": [],
            "leaf_refs": [
              {
                "object_id": "obs_c14_fixture_522a6cbeb84ced83b62def58",
                "revision": 1
              }
            ],
            "unresolved_refs": []
          },
          "summary_dimension": "dim:device_activity",
          "summary_ref": {
            "object_id": "sum_5d6e8d21ef5837c282e05308",
            "revision": 1
          },
          "summary_revision": 1,
          "summary_window": {
            "end": "2026-10-08T23:59:59.999999Z",
            "precision": "day",
            "start": "2026-10-08T00:00:00Z",
            "timezone_name": null,
            "unknown": false
          },
          "wake_ref": {
            "object_id": "wake_2a4d368d389c59d33d4b29dc",
            "revision": 1
          }
        },
        {
          "granularity": "day",
          "grounding_leaf_refs": [
            {
              "object_id": "obs_c14_fixture_6e081d5c46196e1781165d5c",
              "revision": 1
            }
          ],
          "runtime_derived_lineage": {
            "classification": "REALITY",
            "grounding_leaf_refs": [
              {
                "object_id": "obs_c14_fixture_6e081d5c46196e1781165d5c",
                "revision": 1
              }
            ],
            "has_ai_cognition": false,
            "has_maintenance": false,
            "has_reality": true,
            "issues": [],
            "leaf_refs": [
              {
                "object_id": "obs_c14_fixture_6e081d5c46196e1781165d5c",
                "revision": 1
              }
            ],
            "unresolved_refs": []
          },
          "scheduler_derived_lineage": {
            "classification": "REALITY",
            "grounding_leaf_refs": [
              {
                "object_id": "obs_c14_fixture_6e081d5c46196e1781165d5c",
                "revision": 1
              }
            ],
            "has_ai_cognition": false,
            "has_maintenance": false,
            "has_reality": true,
            "issues": [],
            "leaf_refs": [
              {
                "object_id": "obs_c14_fixture_6e081d5c46196e1781165d5c",
                "revision": 1
              }
            ],
            "unresolved_refs": []
          },
          "summary_dimension": "dim:schedule",
          "summary_ref": {
            "object_id": "sum_9d7d45f32dfdab461b21eabe",
            "revision": 1
          },
          "summary_revision": 1,
          "summary_window": {
            "end": "2026-10-08T23:59:59.999999Z",
            "precision": "day",
            "start": "2026-10-08T00:00:00Z",
            "timezone_name": null,
            "unknown": false
          },
          "wake_ref": {
            "object_id": "wake_2d180e13d1006a20d1267907",
            "revision": 1
          }
        },
        {
          "granularity": "day",
          "grounding_leaf_refs": [
            {
              "object_id": "obs_c14_fixture_96ba14d7f113e478b8a8bae8",
              "revision": 1
            }
          ],
          "runtime_derived_lineage": {
            "classification": "REALITY",
            "grounding_leaf_refs": [
              {
                "object_id": "obs_c14_fixture_96ba14d7f113e478b8a8bae8",
                "revision": 1
              }
            ],
            "has_ai_cognition": false,
            "has_maintenance": false,
            "has_reality": true,
            "issues": [],
            "leaf_refs": [
              {
                "object_id": "obs_c14_fixture_96ba14d7f113e478b8a8bae8",
                "revision": 1
              }
            ],
            "unresolved_refs": []
          },
          "scheduler_derived_lineage": {
            "classification": "REALITY",
            "grounding_leaf_refs": [
              {
                "object_id": "obs_c14_fixture_96ba14d7f113e478b8a8bae8",
                "revision": 1
              }
            ],
            "has_ai_cognition": false,
            "has_maintenance": false,
            "has_reality": true,
            "issues": [],
            "leaf_refs": [
              {
                "object_id": "obs_c14_fixture_96ba14d7f113e478b8a8bae8",
                "revision": 1
              }
            ],
            "unresolved_refs": []
          },
          "summary_dimension": "dim:work_outcome",
          "summary_ref": {
            "object_id": "sum_4c759aebb39172f506fd747e",
            "revision": 1
          },
          "summary_revision": 1,
          "summary_window": {
            "end": "2026-10-08T23:59:59.999999Z",
            "precision": "day",
            "start": "2026-10-08T00:00:00Z",
            "timezone_name": null,
            "unknown": false
          },
          "wake_ref": {
            "object_id": "wake_7409ffd83f54190d1406a7f2",
            "revision": 1
          }
        }
      ],
      "silence_is_valid_success": true,
      "step0": {
        "action_allowed": true,
        "delivery_allowed": false,
        "model_allowed": true,
        "reasons": [
          "background_attention_no_user_interrupt"
        ],
        "state": "background"
      },
      "summary_is_semantic_conclusion": false,
      "summary_is_sufficient_evidence_by_itself": false,
      "summary_is_temporal_navigation_anchor": true
    },
    "cognitive_policy_context": {
      "_meta": {
        "included": 0,
        "reader": "read_cognitive_policies",
        "total": 0,
        "truncated": false
      },
      "_policy_records": []
    },
    "wake": {
      "attention_bundle": {
        "execution_contract": "c14_cognitive_derivation",
        "member_count": 4,
        "members": [
          {
            "derived_lineage": {
              "classification": "REALITY",
              "grounding_leaf_refs": [
                {
                  "object_id": "obs_c14_fixture_056dddd04850d813437e8532",
                  "revision": 1
                }
              ],
              "has_ai_cognition": false,
              "has_maintenance": false,
              "has_reality": true,
              "issues": [],
              "leaf_refs": [
                {
                  "object_id": "obs_c14_fixture_056dddd04850d813437e8532",
                  "revision": 1
                }
              ],
              "unresolved_refs": []
            },
            "granularity": "day",
            "hit_count": 1,
            "priority": 50,
            "rule_id": "c14.summary_revision.cognitive_derivation",
            "summary_dimension": "dim:sleep",
            "summary_ref": {
              "object_id": "sum_f25eb0e55e8258fb59baf085",
              "revision": 1
            },
            "summary_window": {
              "end": "2026-10-08T23:59:59.999999Z",
              "precision": "day",
              "start": "2026-10-08T00:00:00Z",
              "timezone_name": null,
              "unknown": false
            },
            "wake_ref": {
              "object_id": "wake_146f08e22bd4f1e6f33a3e12",
              "revision": 1
            },
            "wake_source": "cognitive_derivation"
          },
          {
            "derived_lineage": {
              "classification": "REALITY",
              "grounding_leaf_refs": [
                {
                  "object_id": "obs_c14_fixture_522a6cbeb84ced83b62def58",
                  "revision": 1
                }
              ],
              "has_ai_cognition": false,
              "has_maintenance": false,
              "has_reality": true,
              "issues": [],
              "leaf_refs": [
                {
                  "object_id": "obs_c14_fixture_522a6cbeb84ced83b62def58",
                  "revision": 1
                }
              ],
              "unresolved_refs": []
            },
            "granularity": "day",
            "hit_count": 1,
            "priority": 50,
            "rule_id": "c14.summary_revision.cognitive_derivation",
            "summary_dimension": "dim:device_activity",
            "summary_ref": {
              "object_id": "sum_5d6e8d21ef5837c282e05308",
              "revision": 1
            },
            "summary_window": {
              "end": "2026-10-08T23:59:59.999999Z",
              "precision": "day",
              "start": "2026-10-08T00:00:00Z",
              "timezone_name": null,
              "unknown": false
            },
            "wake_ref": {
              "object_id": "wake_2a4d368d389c59d33d4b29dc",
              "revision": 1
            },
            "wake_source": "cognitive_derivation"
          },
          {
            "derived_lineage": {
              "classification": "REALITY",
              "grounding_leaf_refs": [
                {
                  "object_id": "obs_c14_fixture_6e081d5c46196e1781165d5c",
                  "revision": 1
                }
              ],
              "has_ai_cognition": false,
              "has_maintenance": false,
              "has_reality": true,
              "issues": [],
              "leaf_refs": [
                {
                  "object_id": "obs_c14_fixture_6e081d5c46196e1781165d5c",
                  "revision": 1
                }
              ],
              "unresolved_refs": []
            },
            "granularity": "day",
            "hit_count": 1,
            "priority": 50,
            "rule_id": "c14.summary_revision.cognitive_derivation",
            "summary_dimension": "dim:schedule",
            "summary_ref": {
              "object_id": "sum_9d7d45f32dfdab461b21eabe",
              "revision": 1
            },
            "summary_window": {
              "end": "2026-10-08T23:59:59.999999Z",
              "precision": "day",
              "start": "2026-10-08T00:00:00Z",
              "timezone_name": null,
              "unknown": false
            },
            "wake_ref": {
              "object_id": "wake_2d180e13d1006a20d1267907",
              "revision": 1
            },
            "wake_source": "cognitive_derivation"
          },
          {
            "derived_lineage": {
              "classification": "REALITY",
              "grounding_leaf_refs": [
                {
                  "object_id": "obs_c14_fixture_96ba14d7f113e478b8a8bae8",
                  "revision": 1
                }
              ],
              "has_ai_cognition": false,
              "has_maintenance": false,
              "has_reality": true,
              "issues": [],
              "leaf_refs": [
                {
                  "object_id": "obs_c14_fixture_96ba14d7f113e478b8a8bae8",
                  "revision": 1
                }
              ],
              "unresolved_refs": []
            },
            "granularity": "day",
            "hit_count": 1,
            "priority": 50,
            "rule_id": "c14.summary_revision.cognitive_derivation",
            "summary_dimension": "dim:work_outcome",
            "summary_ref": {
              "object_id": "sum_4c759aebb39172f506fd747e",
              "revision": 1
            },
            "summary_window": {
              "end": "2026-10-08T23:59:59.999999Z",
              "precision": "day",
              "start": "2026-10-08T00:00:00Z",
              "timezone_name": null,
              "unknown": false
            },
            "wake_ref": {
              "object_id": "wake_7409ffd83f54190d1406a7f2",
              "revision": 1
            },
            "wake_source": "cognitive_derivation"
          }
        ]
      },
      "attention_class": "background",
      "budget": {
        "applies": false,
        "available": true,
        "max_model_calls": null,
        "max_wakes": null,
        "model_round_limit": null,
        "policy_refs": [],
        "reasons": [],
        "reserved_model_calls": 0,
        "scope": null,
        "token_usage_available": false,
        "used_model_calls": 0,
        "used_tokens": 0,
        "used_wakes": 0,
        "window_end": null,
        "window_start": null
      },
      "dedupe_key": "attention_bundle:wake_bundle_71c8cb5b630bcdc3161fa4df",
      "effective_wake_source": "cognitive_derivation",
      "evidence_reader": "inspect_world_object",
      "evidence_refs": [
        {
          "object_id": "sum_f25eb0e55e8258fb59baf085",
          "revision": 1
        },
        {
          "object_id": "wake_146f08e22bd4f1e6f33a3e12",
          "revision": 1
        },
        {
          "object_id": "sum_5d6e8d21ef5837c282e05308",
          "revision": 1
        },
        {
          "object_id": "wake_2a4d368d389c59d33d4b29dc",
          "revision": 1
        },
        {
          "object_id": "sum_9d7d45f32dfdab461b21eabe",
          "revision": 1
        },
        {
          "object_id": "wake_2d180e13d1006a20d1267907",
          "revision": 1
        },
        {
          "object_id": "sum_4c759aebb39172f506fd747e",
          "revision": 1
        },
        {
          "object_id": "wake_7409ffd83f54190d1406a7f2",
          "revision": 1
        }
      ],
      "first_hit_at": "2026-10-09T01:10:00+00:00",
      "hit_count": 4,
      "last_hit_at": "2026-10-09T01:10:00+00:00",
      "priority": 50,
      "rule_id": "attention.router.bundle",
      "step0": {
        "action_allowed": true,
        "delivery_allowed": false,
        "model_allowed": true,
        "reasons": [
          "background_attention_no_user_interrupt"
        ],
        "state": "background"
      },
      "wake_ref": {
        "object_id": "wake_bundle_71c8cb5b630bcdc3161fa4df",
        "revision": 2
      },
      "wake_source": "attention_bundle"
    }
  },
  "token_budget": 3400,
  "truncated": true,
  "user_input": "Cognitive derivation bundle wake. The listed pinned Summaries are independent temporal/navigation anchors, not Claims or conclusions. Inspect whichever member leaves, existing cognition, counter-evidence, and cross-dimensional world state you judge relevant. Only form, revise, or retract durable cognition when pinned support closes to qualifying non-Summary reality/case evidence. Silence is a valid successful result. Mechanical bundling makes no semantic claim about the members.",
  "world_map": {
    "as_of": "2026-10-09T01:11:01+00:00",
    "dimension_count": 6,
    "dimensions": [
      {
        "current_object_count": 39,
        "definition_ref": null,
        "dimension": "dim_unclassified",
        "latest_activity_at": "2026-10-09T01:11:01+00:00",
        "lifecycle": null,
        "name": null,
        "object_types": [
          "dependency",
          "wake"
        ],
        "recent_24h_count": 8,
        "recent_7d_count": 38,
        "registered": false
      },
      {
        "current_object_count": 9,
        "definition_ref": null,
        "dimension": "dim:schedule",
        "latest_activity_at": "2026-10-08T15:08:00+00:00",
        "lifecycle": null,
        "name": null,
        "object_types": [
          "observation",
          "summary"
        ],
        "recent_24h_count": 1,
        "recent_7d_count": 4,
        "registered": false
      },
      {
        "current_object_count": 9,
        "definition_ref": null,
        "dimension": "dim:sleep",
        "latest_activity_at": "2026-10-08T13:52:00+00:00",
        "lifecycle": null,
        "name": null,
        "object_types": [
          "observation",
          "summary"
        ],
        "recent_24h_count": 1,
        "recent_7d_count": 4,
        "registered": false
      },
      {
        "current_object_count": 9,
        "definition_ref": null,
        "dimension": "dim:work_outcome",
        "latest_activity_at": "2026-10-08T17:43:00+00:00",
        "lifecycle": null,
        "name": null,
        "object_types": [
          "observation",
          "summary"
        ],
        "recent_24h_count": 1,
        "recent_7d_count": 4,
        "registered": false
      },
      {
        "current_object_count": 3,
        "definition_ref": null,
        "dimension": "dim:conversation",
        "latest_activity_at": "2026-10-09T01:10:00+00:00",
        "lifecycle": null,
        "name": null,
        "object_types": [
          "observation",
          "summary"
        ],
        "recent_24h_count": 1,
        "recent_7d_count": 3,
        "registered": false
      },
      {
        "current_object_count": 7,
        "definition_ref": null,
        "dimension": "dim:device_activity",
        "latest_activity_at": "2026-10-08T17:38:00+00:00",
        "lifecycle": null,
        "name": null,
        "object_types": [
          "observation",
          "summary"
        ],
        "recent_24h_count": 1,
        "recent_7d_count": 2,
        "registered": false
      }
    ],
    "directory_only": true,
    "expand_capabilities": {
      "broader_recall": "expand_recall",
      "dimension_definitions": "list_dimensions",
      "exact_object": "inspect_world_object",
      "multi_dimension_window": "request_all_dimensions_projection",
      "refresh_directory": "read_world_map",
      "semantic_recall": "search_world",
      "single_dimension_timeline": "search_timeline"
    },
    "index_lag": 0,
    "index_watermark": 80,
    "schema": "aios.world-map.l0.v1",
    "semantic_conclusions": false,
    "truncated": false,
    "world_revision": 80
  }
}
```

## capability_history

```json
[]
```

## capability_catalog

```json
[
  {
    "description": "Persist a typed AI-world cognition using the unified EvidenceSet + Claim + Dependency path.",
    "hard_boundary": false,
    "input_schema": {
      "claim_type": "string?",
      "confidence": "number[0,1]",
      "domain": "user_understanding|relationship|self|intent|strategy|cognitive_boundary|personality|calibration",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "knowledge_state": "string?",
      "scope_key": "string?",
      "statement": "string",
      "tags": "array[string]?"
    },
    "kind": "write",
    "name": "commit_ai_world_claim",
    "side_effecting": true
  },
  {
    "description": "Persist a revisable AI cognition Claim grounded in pinned world evidence. This capability cannot create Observation facts.",
    "hard_boundary": false,
    "input_schema": {
      "claim_type": "string?",
      "confidence": "number[0,1]",
      "content": "string",
      "dimension": "string",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "knowledge_state": "string?"
    },
    "kind": "write",
    "name": "commit_claim",
    "side_effecting": true
  },
  {
    "description": "During an active periodic review, persist a model-authored operation experience grounded in pinned real case refs.",
    "hard_boundary": false,
    "input_schema": {
      "applicability": "object?",
      "cost": "object[number]?",
      "experience_state": "string?",
      "method_path": "array[string]",
      "misses": "array[string]?",
      "negative_case_refs": "array[{object_id:string,revision:integer}]?",
      "positive_case_refs": "array[{object_id:string,revision:integer}]?",
      "problem_type": "string",
      "result_summary": "string"
    },
    "kind": "write",
    "name": "commit_operation_experience",
    "side_effecting": true
  },
  {
    "description": "Inspect multiple pinned Claims side by side with their evidence/status; the model decides meaning.",
    "hard_boundary": false,
    "input_schema": {
      "claim_refs": "array[{object_id:string,revision:integer}]"
    },
    "kind": "read",
    "name": "compare_claims",
    "side_effecting": false
  },
  {
    "description": "Register future attention as a constrained mechanical Observation watch. The Resident chooses the routing class: interrupt wakes cognition immediately and may allow user delivery after Resident judgment; background waits for short mechanical batching, invokes cognition, and is silent to the user by default; review_queue does not invoke the Resident immediately and carries matched evidence into Periodic Review. Choose the class from the future-attention intent and current runtime facts; Core does not infer urgency for you. Do not encode emotion, intent, diagnosis, or other semantic conclusions in the mechanical predicate.",
    "hard_boundary": false,
    "input_schema": {
      "attention_class": "interrupt|background|review_queue?",
      "cooldown_seconds": "integer?",
      "dimensions": "array[string]",
      "expires_at": "ISO-8601 datetime?",
      "goal_ref": "{object_id:string,revision:integer}?",
      "metadata_equals": "object?",
      "modality": "string?",
      "mode": "recurring|one_shot?",
      "numeric": "{operator:gt|gte|lt|lte|eq|ne,threshold:number,path:array[string]?}?",
      "priority": "integer?",
      "reason_refs": "array[{object_id:string,revision:integer}]",
      "source_kind": "string?",
      "title": "string"
    },
    "kind": "write",
    "name": "create_attention_watch",
    "side_effecting": true
  },
  {
    "description": "Create a concrete evidence-grounded Task, optionally under a current Goal.",
    "hard_boundary": false,
    "input_schema": {
      "completion_condition": "object?; use mode=world_evidence|action_outcome|mixed; optional result_object_types=array[string]",
      "deadline": "ISO-8601 datetime?",
      "goal_ref": "{object_id:string,revision:integer}?",
      "initial_state": "string?",
      "next_step": "string?",
      "next_wake_at": "ISO-8601 datetime?",
      "priority": "integer?",
      "reason_refs": "array[{object_id:string,revision:integer}]",
      "task_type": "string",
      "timezone_name": "string?",
      "title": "string"
    },
    "kind": "write",
    "name": "create_task",
    "side_effecting": true
  },
  {
    "description": "Read exact pinned raw dialogue behind a same-session round summary, or an explicit turn range. Round summaries are indexes, not truth.",
    "hard_boundary": false,
    "input_schema": {
      "revision": "integer?",
      "session_id": "string?",
      "summary_id": "string?",
      "turn_end": "integer?",
      "turn_start": "integer?"
    },
    "kind": "read",
    "name": "drill_down_conversation",
    "side_effecting": false
  },
  {
    "description": "Request a broader bounded world recall after the initial recommendation/search was insufficient.",
    "hard_boundary": false,
    "input_schema": {
      "dimension": "string?",
      "limit": "integer?",
      "query": "string"
    },
    "kind": "read",
    "name": "expand_recall",
    "side_effecting": false
  },
  {
    "description": "Focus retrieval on one known Entity id without semantic reinterpretation.",
    "hard_boundary": false,
    "input_schema": {
      "entity_id": "string",
      "limit": "integer?",
      "query": "string?"
    },
    "kind": "read",
    "name": "focus_entity",
    "side_effecting": false
  },
  {
    "description": "Follow one-hop explicit Relation objects connected to a world object.",
    "hard_boundary": false,
    "input_schema": {
      "limit": "integer?",
      "object_id": "string"
    },
    "kind": "read",
    "name": "follow_relation",
    "side_effecting": false
  },
  {
    "description": "Form a revisable Event candidate from pinned world evidence. The model supplies the event meaning; code only validates provenance.",
    "hard_boundary": false,
    "input_schema": {
      "confidence": "number[0,1]",
      "dimension": "string?",
      "event_time": "TemporalExtent object",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "interpretation": "string",
      "participant_refs": "array[{object_id:string,revision:integer}]?",
      "primary_claim_refs": "array[{object_id:string,revision:integer}]?",
      "title": "string"
    },
    "kind": "write",
    "name": "form_event",
    "side_effecting": true
  },
  {
    "description": "Inspect a pinned real Action Outcome and its Action reference.",
    "hard_boundary": false,
    "input_schema": {
      "outcome_ref": "{object_id:string,revision:integer}"
    },
    "kind": "read",
    "name": "inspect_outcome",
    "side_effecting": false
  },
  {
    "description": "Read one pinned or latest world object by object id.",
    "hard_boundary": false,
    "input_schema": {
      "object_id": "string",
      "revision": "integer?"
    },
    "kind": "read",
    "name": "inspect_world_object",
    "side_effecting": false
  },
  {
    "description": "List Resident-authored active attention watches. Watches contain only mechanical future-match predicates; the Resident interprets meaning after Wake.",
    "hard_boundary": false,
    "input_schema": {},
    "kind": "read",
    "name": "list_attention_watches",
    "side_effecting": false
  },
  {
    "description": "List same-session continuity summary windows on demand. Use this when token budgeting omitted summary content from the cockpit.",
    "hard_boundary": false,
    "input_schema": {
      "limit": "integer?",
      "session_id": "string?"
    },
    "kind": "read",
    "name": "list_conversation_summaries",
    "side_effecting": false
  },
  {
    "description": "List current registered dimension definitions so the resident AI can check whether an existing observation axis already serves the need.",
    "hard_boundary": false,
    "input_schema": {
      "include_terminal": "boolean?"
    },
    "kind": "read",
    "name": "list_dimensions",
    "side_effecting": false
  },
  {
    "description": "Create a PROPOSED external Action for a RUNNING Task. This capability never executes the side effect and cannot authorize itself.",
    "hard_boundary": false,
    "input_schema": {
      "action_type": "string",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "expected_outcome": "string?",
      "payload": "object",
      "task_ref": "{object_id:string,revision:integer}"
    },
    "kind": "write",
    "name": "propose_action",
    "side_effecting": true
  },
  {
    "description": "Register a new evidence-grounded AI-mutable cognitive policy. Only real user/world result evidence is accepted; hard boundaries cannot be created by the resident AI.",
    "hard_boundary": false,
    "input_schema": {
      "allowed_range_or_choices": "json value?",
      "current_value": "json value",
      "default_value": "json value",
      "evaluation_window": "string",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "policy_id": "string",
      "reason": "string",
      "scope": "string"
    },
    "kind": "write",
    "name": "propose_cognitive_policy",
    "side_effecting": true
  },
  {
    "description": "Submit an evidence-grounded candidate observation axis. The system validates structure; the model supplies semantic rationale.",
    "hard_boundary": false,
    "input_schema": {
      "confidence": "number[0,1]",
      "continuity_rationale": "string",
      "data_shape": "string",
      "description": "string",
      "dimension_key": "string starting dim:",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "expected_value": "string?",
      "maintenance_cost_rationale": "string",
      "name": "string",
      "update_method": "string?",
      "user_value_rationale": "string",
      "why_existing_dimensions_are_insufficient": "string"
    },
    "kind": "write",
    "name": "propose_dimension",
    "side_effecting": true
  },
  {
    "description": "Create a durable Entity anchor from pinned same-world evidence. The resident supplies identity meaning; Core enforces explicit entity_key and provenance.",
    "hard_boundary": false,
    "input_schema": {
      "aliases": "array[string]?",
      "canonical_name": "string?",
      "entity_key": "string",
      "entity_kind": "string",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "identity_claim_refs": "array[{object_id:string,revision:integer}]?"
    },
    "kind": "write",
    "name": "propose_entity",
    "side_effecting": true
  },
  {
    "description": "Create an evidence-grounded Goal proposal in the unified world. A proposal does not grant external-action authorization.",
    "hard_boundary": false,
    "input_schema": {
      "confidence": "number[0,1]",
      "description": "string",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "source_type": "user_explicit|user_inferred|ai_self|app|external",
      "success_criteria": "array[string]?",
      "title": "string"
    },
    "kind": "write",
    "name": "propose_goal",
    "side_effecting": true
  },
  {
    "description": "Read current evidence-grounded AI cognition across user understanding, relationship, self, intent, strategy, boundary, personality and calibration.",
    "hard_boundary": false,
    "input_schema": {
      "domains": "array[string]?",
      "limit": "integer?",
      "scope_key": "string?"
    },
    "kind": "read",
    "name": "read_ai_world",
    "side_effecting": false
  },
  {
    "description": "Read the current mechanical BACKGROUND_DAY budget and durable usage. This reports policy caps, Wake/model-call usage and remaining capacity only; it does not decide which future fact is important.",
    "hard_boundary": false,
    "input_schema": {},
    "kind": "read",
    "name": "read_background_budget",
    "side_effecting": false
  },
  {
    "description": "Read current versioned R6 policy records from the unified world.",
    "hard_boundary": false,
    "input_schema": {
      "policy_id": "string?"
    },
    "kind": "read",
    "name": "read_cognitive_policies",
    "side_effecting": false
  },
  {
    "description": "Read current Goals, Tasks and proposed/executed Actions from the unified world. This is a read-only planning view.",
    "hard_boundary": false,
    "input_schema": {},
    "kind": "read",
    "name": "read_execution_world",
    "side_effecting": false
  },
  {
    "description": "Read a bounded page of the evidence anchors selected for the currently active periodic review. Available only during review.",
    "hard_boundary": false,
    "input_schema": {
      "limit": "integer?",
      "offset": "integer?"
    },
    "kind": "read",
    "name": "read_periodic_review_anchors",
    "side_effecting": false
  },
  {
    "description": "Refresh the compact L0 world-map directory. Returns dimension identity, mechanical activity/count metadata and expansion capability names only; it does not return dimension payloads or semantic conclusions.",
    "hard_boundary": false,
    "input_schema": {},
    "kind": "read",
    "name": "read_world_map",
    "side_effecting": false
  },
  {
    "description": "Record what communication style was used and the real user/world reaction. This records evidence only and does not choose a future style.",
    "hard_boundary": false,
    "input_schema": {
      "action_ref": "{object_id:string,revision:integer}?",
      "applicable_conditions": "object?",
      "counterexample_refs": "array[{object_id:string,revision:integer}]?",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "scenario": "string",
      "style": "string",
      "tone": "string?",
      "user_reaction": "accepted|resisted|ignored|unknown"
    },
    "kind": "write",
    "name": "record_communication_experience",
    "side_effecting": true
  },
  {
    "description": "Observe several parallel dimensions in one time window without turning co-occurrence into a causal conclusion.",
    "hard_boundary": false,
    "input_schema": {
      "dimensions": "array[string]",
      "query": "string?",
      "window_end": "ISO-8601 datetime",
      "window_start": "ISO-8601 datetime"
    },
    "kind": "read",
    "name": "request_all_dimensions_projection",
    "side_effecting": false
  },
  {
    "description": "Retract the current Claim using pinned contrary/correcting evidence and propagate review-required state to dependents.",
    "hard_boundary": false,
    "input_schema": {
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "reason": "string",
      "target_ref": "{object_id:string,revision:integer}"
    },
    "kind": "write",
    "name": "retract_claim",
    "side_effecting": true
  },
  {
    "description": "Retrieve an exact Observation fact by id/revision for evidence drill-down.",
    "hard_boundary": false,
    "input_schema": {
      "object_id": "string",
      "revision": "integer?"
    },
    "kind": "read",
    "name": "retrieve_original_observation",
    "side_effecting": false
  },
  {
    "description": "Create a forward-only new revision of the current Claim and mark dependent cognition review-required.",
    "hard_boundary": false,
    "input_schema": {
      "confidence": "number[0,1]?",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "reason": "string",
      "replacement_content": "string",
      "target_ref": "{object_id:string,revision:integer}"
    },
    "kind": "write",
    "name": "revise_claim",
    "side_effecting": true
  },
  {
    "description": "Append a new revision of the current Entity identity anchor using pinned evidence.",
    "hard_boundary": false,
    "input_schema": {
      "aliases": "array[string]?",
      "canonical_name": "string?",
      "entity_ref": "{object_id:string,revision:integer}",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "identity_claim_refs": "array[{object_id:string,revision:integer}]?",
      "reason": "string"
    },
    "kind": "write",
    "name": "revise_entity",
    "side_effecting": true
  },
  {
    "description": "Forward-append a rollback to an earlier policy version using pinned evidence.",
    "hard_boundary": false,
    "input_schema": {
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "policy_id": "string",
      "reason": "string",
      "target_version": "integer"
    },
    "kind": "write",
    "name": "rollback_cognitive_policy",
    "side_effecting": true
  },
  {
    "description": "Search same-session round-summary indexes by topic/text, then drill down to exact pinned raw dialogue when precision is needed.",
    "hard_boundary": false,
    "input_schema": {
      "limit": "integer?",
      "query": "string",
      "session_id": "string?"
    },
    "kind": "read",
    "name": "search_conversation_summaries",
    "side_effecting": false
  },
  {
    "description": "Search the world inside an explicit time window, optionally bounded by dimension/type/query.",
    "hard_boundary": false,
    "input_schema": {
      "dimension": "string?",
      "limit": "integer?",
      "object_types": "array[string]?",
      "query": "string?",
      "window_end": "ISO-8601 datetime",
      "window_start": "ISO-8601 datetime"
    },
    "kind": "read",
    "name": "search_timeline",
    "side_effecting": false
  },
  {
    "description": "Recall candidate world objects related to a query.",
    "hard_boundary": false,
    "input_schema": {
      "limit": "integer?",
      "query": "string"
    },
    "kind": "read",
    "name": "search_world",
    "side_effecting": false
  },
  {
    "description": "Move the current dimension revision through a legal lifecycle transition using pinned evidence and an AI-supplied reason.",
    "hard_boundary": false,
    "input_schema": {
      "dimension_ref": "{object_id:string,revision:integer}",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "new_lifecycle": "candidate|trial|active|low_activity|dormant|merged|split|revised|rejected|reactivated|archived",
      "reason": "string",
      "related_dimension_refs": "array[{object_id:string,revision:integer}]?"
    },
    "kind": "write",
    "name": "transition_dimension",
    "side_effecting": true
  },
  {
    "description": "Forward-revise/resolve/reject/merge/split the current Event using pinned evidence.",
    "hard_boundary": false,
    "input_schema": {
      "confidence": "number[0,1]?",
      "event_ref": "{object_id:string,revision:integer}",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "new_status": "candidate|active|resolved|revised|rejected|merged|split",
      "reason": "string",
      "related_event_refs": "array[{object_id:string,revision:integer}]?",
      "replacement_interpretation": "string?",
      "replacement_title": "string?"
    },
    "kind": "write",
    "name": "transition_event",
    "side_effecting": true
  },
  {
    "description": "Move the current Goal revision through a legal evidence-backed state transition.",
    "hard_boundary": false,
    "input_schema": {
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "goal_ref": "{object_id:string,revision:integer}",
      "new_status": "proposed|active|paused|achieved|abandoned|unknown",
      "reason": "string"
    },
    "kind": "write",
    "name": "transition_goal",
    "side_effecting": true
  },
  {
    "description": "Move the current Task revision through a legal state transition. Terminal transitions obey the Task's explicit completion mode: WORLD_EVIDENCE uses pinned durable evidence; ACTION_OUTCOME requires a real authorized Action-linked Outcome; MIXED requires both.",
    "hard_boundary": false,
    "input_schema": {
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "execution_refs": "array[{object_id:string,revision:integer}]?",
      "new_state": "string",
      "next_step": "string?",
      "next_wake_at": "ISO-8601 datetime?",
      "outcome_refs": "array[{object_id:string,revision:integer}]?",
      "reason": "string",
      "task_ref": "{object_id:string,revision:integer}"
    },
    "kind": "write",
    "name": "transition_task",
    "side_effecting": true
  },
  {
    "description": "Append an evidence-grounded value revision to an already-registered AI-mutable cognitive policy. Cannot create or loosen hard boundaries.",
    "hard_boundary": false,
    "input_schema": {
      "current_value": "json value",
      "evaluation_window": "string?",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "policy_id": "string",
      "reason": "string"
    },
    "kind": "write",
    "name": "update_cognitive_policy",
    "side_effecting": true
  },
  {
    "description": "Create or forward-revise an evidence-grounded Relation between current Entity revisions.",
    "hard_boundary": false,
    "input_schema": {
      "confidence": "number[0,1]",
      "evidence_refs": "array[{object_id:string,revision:integer}]",
      "left_ref": "{object_id:string,revision:integer}",
      "reason": "string",
      "relation_type": "string",
      "right_ref": "{object_id:string,revision:integer}",
      "valid_time": "TemporalExtent object?"
    },
    "kind": "write",
    "name": "upsert_relation",
    "side_effecting": true
  }
]
```
