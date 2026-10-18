.PHONY: up matrix report export check
up:
	docker compose up -d
matrix:
	docker compose run --rm runner python -m harness.run_all --grader all && docker compose run --rm runner python -m harness.report --latest
report:
	docker compose run --rm runner python -m harness.report --latest
export:
	docker compose run --rm runner python -m harness.export_harbor --validate
check:
	docker compose run --rm runner python -m pytest harness/tests -q
	docker compose run --rm runner python tools/check_lock.py
	docker compose run --rm runner python -m harness.check_realism
	docker compose run --rm runner python -m harness.lint_leaks
	docker compose run --rm runner python -m harness.alt_distance
	docker compose run --rm runner python -m harness.export_harbor --validate
	docker compose run --rm runner python -m harness.check_done
