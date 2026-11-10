# Task board: apni-awaaz

Claim a task before starting: owner and branch, then push this file. A claim with no pushed progress for 3 hours can be taken over (note it here).
Owners: **NP** = Nitya · **TM** = teammate (plus AI assistant) · **CL** = Claude on Nitya's laptop.
Plan: `docs/03-build-plan.md`. Engine contract: `voice-core/README.md` (the engine is built in `dadi-vs-scammers` first; sync it before Task 2).

| # | Task | Owner | Branch | Status |
|---|---|---|---|---|
| 0 | Bootstrap | CL | main | done (workspace, frontend copy, engine sync) |
| 1 | see plan | TM | feat/tm-awaaz | done (fakes only; needs live test) |
| 2 | see plan | TM | feat/tm-awaaz | done (fakes only; needs live test) |
| 3 | see plan | TM | feat/tm-awaaz | done (fakes only; needs live test) |
| 4 | see plan | TM | feat/tm-awaaz | done (fakes only; needs live test) |
| 5 | see plan | TM | feat/tm-awaaz | done (fakes only; needs live test) |
| 6 | see plan (live test + demo) | | | todo |
| 7 | see plan (Pukaar only) | | | todo |
| 8 | see plan (Pukaar only) | | | todo |
| 9 | see plan (Pukaar only) | | | todo |

## Log
- Sun 8 Nov 11:30: docs, design, plan and bootstrap (CL).
- Sun 8 Nov 13:40: Tasks 1-5 on `feat/tm-awaaz`: quality check, profiles, speak, converse, FastAPI app, fake mode (AWAAZ_FAKE=1), web app (TM). Not yet tested with real keys.
- Tue 10 Nov 18:40: review on `feat/cl-awaaz-review` (CL): 16 findings, 15 fix commits. Gnani REST gate with a 429 retry, delete-my-voice also wipes cloned audio, SOS falls back to the phone's voice, the first scanning switch press no longer turns scanning off, no stale app from the service worker, no mic left on. Tests 48 → 54. Report: `docs/review-cl-2026-11-10.md`; screenshots: `docs/screenshots/final/`.
