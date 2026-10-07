.PHONY: check lint test

check: lint test

lint:
	poetry run flake8 src/ tests/
	poetry run black --check src/ tests/
	poetry run bandit -r src/ -q
	poetry run mypy src/

test:
	poetry run pytest --cov=src --cov-report=term-missing --cov-fail-under=90 -q
