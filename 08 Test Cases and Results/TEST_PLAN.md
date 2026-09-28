# Test strategy and acceptance evidence

Baseline automated output is in AUTOMATED_RESULTS.txt: 42 regression checks and a separate end-to-end missing-GTM claim/protected-card check passed. This is agent-run evidence, not a statement that students independently ran it. Test source is in the repository snapshot; final release execution belongs in [[TEAM_TEST_RESULTS]].

Use an isolated copy with a fresh SQLite database and synthetic files. Preserve original model artifacts and hash the tested source. Run python -m pytest tests -q from the source root with PYTHONPATH=src;. (Windows) or src:. (POSIX). The current tests use the database resolved under their source tree, so do not run them against the working application folder containing live data.

Functional: exercise registration/login/profile/product/warranty/intake/review/status/report flows for every role. Integration: connect document extraction, correction, features, both genuine models, persistence and reviewer actions. Database: verify ownership, foreign-key relationships, uniqueness, concurrent IDs, rollback and immutable historical evaluations. Negative: malformed dates/numbers, empty/oversized/mislabeled files, missing artifacts, unavailable database and unauthorized requests. Security: cross-user URLs/downloads, forged roles, session behavior, password migration, validation and information disclosure. OCR: embedded-text PDF, scanned PDF and image receipts, bad scans, date formats, serial errors and corrected values.

Model tests: correct label order, three finite probabilities, model hash, unavailable-state behavior and truly separate model inputs. Comparison tests: just below/at/above each threshold and disagreeing top classes. Rule tests: all categories, grace/deadline limits, exclusions, mandatory evidence and changed policies. Contradiction/duplicate tests: date order, model/serial mismatch and repeated hashes/invoice/serial evidence. Low-confidence/disagreement must route to review.

MANDATORY_SCENARIOS.csv contains all eleven demonstration scenarios with separate expected and actual columns. Do not put expected values into Actual without executing. Capture genuine model disagreements when filming; controlled fixtures are labeled unit-test evidence only.

## Hidden test readiness

Verify no hard-coded case answers; no label/prediction leakage on cards; unknown categories handled; policy/threshold changes reload; all evidence variants retain their split; missing-model state is explicit; required roles cannot read another user's files; malformed input yields understandable messages; original AI results survive override; team can explain and modify each module. Record final review [[HIDDEN_TEST_REVIEW]].

Independent tester [[TEAM_TESTER]]; execution date [[TEAM_TEST_DATE]]; source commit [[RELEASE_COMMIT]]; environment [[RELEASE_RUNTIME]]; screenshot evidence [[SCENARIO_SCREENSHOTS]].
