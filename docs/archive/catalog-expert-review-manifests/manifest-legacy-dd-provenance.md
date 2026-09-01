# §7.3 Legacy DD-source provenance — export-gate evidence (orchestrator, read-only)

## Invariant query result (live graph, 2026-07-15)
- DD StandardNameSource nodes total: **8741**
- `dd_snapshot_pinned = true`: **0**
- unpinned (null/false): **8741**
- unpinned feeding an **accepted** name (would block export): **3963**

## Legacy node shape
Legacy DD-source nodes carry NO `dd_version` (all None) and NO pinned raw
leaf/parent doc snapshot. They carry: id (=`dd:<path>`), description,
physics_domain, batch_key, composed_at (~2026-06-18), produced_sn_id, status.
The exact DD version at extraction is NOT recorded on the node — §7.3 forbids
inferring it from the node.

## Authoritative run/release evidence available
- imas-codex depends on `imas_data_dictionaries==4.1.1` (uv.lock, wheel
  uploaded 2026-01-15).
- SN seeding policy is strictly current-DD (project invariant; memory
  "DD version gate": DDv3 ledger purged 2026-07-10, seeding current-DD only).
- Graph dominant IDS version = 4.1.1; exactly one DDVersion node is_current.
- DDVersion nodes do NOT expose a `version` string property (only is_current) —
  version anchor is the installed package, not a graph node field.

## Consequence
Hard stop §7.7: "Do not export while the direct source invariant query finds
any unpinned or incomplete legacy DD source." → catalog RC export
(§7.6 / f-final-editorial-export) is BLOCKED until this is resolved.

## Decision required (user)
- (A) Reviewed one-off backfill: capture pinned snapshots for the 8741 legacy
  sources against the current DD 4.1.1 (defensible because seeding is
  strictly current-DD and 4.1.1 is the pinned/installed release). Reviewed
  dry-run manifest first; migration driver removed after execution (§7.3).
- (B) Regeneration proposal: re-extract affected names against named DD 4.1.1.
  Heavier; only if backfill can't prove per-source provenance.
- (C) Defer export; land all non-export remediation now, cut RC later.

Needs: confirmation that 4.1.1 was the pinned DD across the 2026-06-18
extraction window (no intervening DD bump). If a bump occurred mid-window,
backfill must partition by composed_at.
