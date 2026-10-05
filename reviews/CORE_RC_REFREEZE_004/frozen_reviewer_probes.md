# CORE-RC-REFREEZE-004 - Frozen historical reviewer probes

The probes are extracted fresh from canonical reviewer commits, not copied from author evidence.

## Identities

- Window 20 Suite A: review `220311759e88fb3948ad3f4dba655058e0f392a8`, blob `527edd8d92243cabc417f176c0f7c4f6c358e65c`, SHA-256 `ec1dc5c2c5406d5d9e74825f62e0a17fb80f8ebd6dc250817fa048511ce292b5`.
- Window 20 Suite B: review `220311759e88fb3948ad3f4dba655058e0f392a8`, blob `867f0ee993595c2d334a3940ad66308166693c97`, SHA-256 `769242465817f31734661ba7ba9c3d5f7d06b8d3f5235d72d2026956d9b98eb1`.
- Window 17: review `e4161dd0ad0a2f825461311a1c8c5ff8234a07f8`, blob `bb25d184a5cb813ae4058de9a75fa23d9591b041`, SHA-256 `a6db33956bb7bc1e8af19cddd7cebdd320604bba98b6a2b906fd1eb363fba0c3`.

## Fresh RC004 preflight result

Run `37210904177`:
- Suite A: **4 probes / 0 failures**
- Suite B: **7 probes / 0 failures**
- W17: **14 probes / 0 failures**

The final exact-head run repeats extraction, blob verification, SHA-256 verification and execution. Its result is binding.
