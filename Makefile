UV = uv run --frozen
PYTHON_FILES = src tests docs/conf.py

.PHONY: ci ci-docker
ci:
	$(UV) ruff check .
	$(UV) ruff format --check .
	$(UV) black --check $(PYTHON_FILES)
	$(UV) isort --check-only $(PYTHON_FILES)
	$(UV) flake8 --max-line-length=88 --extend-ignore=E203 $(PYTHON_FILES)
	$(UV) pyright
	$(UV) pytest -q

ci-docker:
	docker run --rm -v "$(CURDIR):/src:ro" -w /src -e PYTHONDONTWRITEBYTECODE=1 python:3.13 sh -ec 'pip install --quiet uv && mkdir /tmp/checkout && tar --exclude=.venv --exclude=.git --exclude=.ruff_cache --exclude=.pytest_cache -cf - . | tar -xf - -C /tmp/checkout && cd /tmp/checkout && make ci'

.PHONY: docs
docs:
	uv run --frozen --group docs sphinx-build -W -b html docs docs/_build/html
