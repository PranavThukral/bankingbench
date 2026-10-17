# Harbor format notes (fetched 2026-10-17 from docs.harborframework.com/tasks/configuration and /tasks/overview)

Task dir: instruction.md, task.toml, environment/ (Dockerfile, or docker-compose.yaml for multi-container), solution/solve.sh (+files), tests/test.sh (+files).
Rewards: /logs/verifier/reward.txt (single number) or /logs/verifier/reward.json (multi-dimensional/labeled).

task.toml keys (verified):
- top level: schema_version (str, default "1.3"), multi_step_reward_strategy, source (str|null)
- [task]: name ("org/name", required if table present), authors (list of {name, email?}), description (str), keywords (list[str])
- [metadata]: arbitrary author-defined table
- [verifier]: timeout_sec (number, default 600), network_mode ("no-network"|"public"|"allowlist"), allowed_hosts, env (table), user, environment_mode ("shared"|"separate")
- [agent]: timeout_sec, network_mode, allowed_hosts, user
- [solution]: env (table)
- [environment]: build_timeout_sec, network_mode, allowed_hosts, docker_image, os ("linux"|"windows"), cpus, memory_mb, storage_mb, gpus, gpu_types, env, healthcheck {command, interval_sec, timeout_sec, start_period_sec, start_interval_sec, retries}, workdir
- artifacts: list

NOT documented on those pages (do not invent): mount paths for /tests and /solution, env vars available to test.sh, compose file conventions. Treat these as assumptions and say so in comments.
