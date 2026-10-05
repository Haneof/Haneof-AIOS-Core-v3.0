# CORE-RC-REFREEZE-004 - Clean install / headless evidence

Fresh preflight run `37210904177` built a wheel from the exact frozen software, installed it **non-editably** into a fresh virtual environment, and ran `aios-core-headless`.

Result: `HEADLESS_CLEAN_INSTALL_PASS`.

Observed lifecycle:
1. clean disposable World/index start at revision 0;
2. deterministic mechanical turn -> `HEADLESS_MECHANICAL_OK`, World revision 2;
3. fresh OS process reopen -> same World revision, index watermark 2, lag 0;
4. provider-free `recovery-status` -> safe `AUTO_RECOVERABLE`;
5. final clean reopen -> continuity preserved.

Five separate CLI processes were used. No real provider and no Resident fixture/semantics were used.

The final exact-head workflow repeats this gate and is binding.
