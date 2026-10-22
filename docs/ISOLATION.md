# Verdict isolation: what is prevented and what is not

The grader runs the candidate's code inside the pytest process that grades it, so a hostile
solution shares an address space with the verdict machinery. This note records what the harness
does about that (review finding F17) and what it cannot.

## Now prevented

| Attack | Defence |
| --- | --- |
| Rewrite `junit.xml` with one passing test and exit 0 (the `forge_junit` probe) | The expected-test manifest is collected in a separate pytest process whose path holds the trusted starter, never the candidate workspace (AST function names are the fallback). Every expected test must appear in the JUnit results; missing, extra or renamed tests give `infra_error`. |
| Exit 0 over real failures, or a hand-written exit code | pytest's exit code and its final summary line must agree with the JUnit counts; any mismatch gives `infra_error`. Skips still count as failures. |
| Read `PG_ADMIN_URL` or other harness secrets from `os.environ` | The candidate receives an allow-listed environment only: `PATH`, `SYSTEMROOT`/`TEMP` and similar, the determinism variables, `DATABASE_URL`, `PYTHONPATH`. |
| Use the superuser connection to read or change other databases or roles | `DATABASE_URL` names a per-run `NOSUPERUSER NOCREATEDB NOCREATEROLE` role that owns only the per-run database. `CONNECT` on that database is revoked from `PUBLIC`, so concurrent runs cannot open each other's. Role and database are dropped afterwards; a failed drop is logged and makes the run `infra_error`. |

The Harbor `tests/verify.py` mirrors all four: it ships `manifest.json` (built at export time from the
starter), the same JUnit checker and the same role-per-run database helper.

## Still not prevented

- **Same OS user, same machine.** The candidate can read the grader copy at `<run>/grader`, `graderlib`,
  the JUnit path (visible in `sys.argv`), the other run directories under the temp folder, and the
  repository, including `heldout/` and `results/`. Reading the hidden tests is not detected.
- **A complete forgery.** A candidate that learns the full expected test list can write a JUnit file with
  every test passing, print a matching summary line and exit 0 from inside the pytest process. The
  checks above only catch forgeries that are incomplete or inconsistent.
- **Tampering with the grader at run time** (monkeypatching `pytest`, `graderlib` or assertions in-process).
- The catalog `postgres` database and role list stay visible to the per-run role, and CPU, disk and
  network are not limited natively.

## Real isolation

Real isolation needs the candidate and the verifier in different trust domains: separate containers
(or at least separate OS users), the tests mounted read-only only at verification time, a verifier
process that never imports candidate code and reads results through a channel the candidate cannot
write, and no network. Harbor provides that shape (`/tests` appears only when verification starts);
this repository's native runner does not claim it. Treat native results as an authoring aid and a
defence against accidents and naive hacks, not as a security boundary.
