# Seeded fixtures (port acceptance)

A port of a skill is incomplete until it recovers the known planted defects at the declared severities and marks the planted-clean modules `EXAMINED` with a substantive invariant.

```
python3 <qc-core>/scripts/verify_port.py \
  --expected <qc-core>/fixtures/<skill>/expected.json \
  --ledger .qc-findings/qc-<skill>.json \
  --profile .qc-profile.json
```

| Fixture | What is planted |
|---------|-----------------|
| `fixtures/hardening/repo` | Hardcoded secret (P0, mechanical) + `str.strip` on a value that can be `None` (P1) + a clean `add()` module |
| `fixtures/coherence/repo` | Same identifier under two names + a production `NotImplementedError` stub + a clean module |
| `fixtures/docs/repo` | README command that does not exist in the CLI |

Do not "fix" the fixtures to make a weak port pass. The expected set is the acceptance test.

The deterministic CI fixtures under `qc-all/references/fixtures/` (ruff/mypy/test-fail injectors) are a different contract — they test `qc_deterministic.sh`, not a skill port.
