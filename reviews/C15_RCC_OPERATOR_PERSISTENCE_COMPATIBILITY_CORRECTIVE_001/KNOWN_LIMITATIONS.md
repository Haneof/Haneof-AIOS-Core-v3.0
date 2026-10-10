# KNOWN LIMITATIONS & FUTURE BOUNDARIES

- **Task**: `C15-RCC-OPERATOR-PERSISTENCE-COMPATIBILITY-CORRECTIVE-001`
- **Scope**: Boundaries and known operational constraints for C15 persistence harness.

---

## 1. Known Limitations

1. **Synthetic Key Material for C15 Test Harness**:
   - The RSA key pair embedded in `tools/c15_persistence/provider.py` is dedicated to the C15 synthetic relay / provider testing framework. In production, real hardware secure enclave or external cloud providers will bind their respective cryptographic key identities.

2. **Single-Writer Constraint**:
   - As per AIOS Core architecture, `OperatorSession` assumes a single-writer process model per session root. Concurrent writer arbitration is handled by backend locking (`backend.lock()`).

3. **Subprocess Kill Tests on Windows/WSL**:
   - Direct file permission manipulations (`0o000`) on Linux/WSL behave differently under root vs unprivileged users; the codebase includes explicit permission mode checks to maintain strict security across all environments.
