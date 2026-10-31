.RECIPEPREFIX = >
.PHONY: lint test test-live check sync-docs install

lint:
> uv run ruff check .
> uv run ruff format --check .
> find bin templates -name '*.sh' -o -path 'bin/*' -type f 2>/dev/null | xargs -r shellcheck
> bin/mdlint

test:
> uv run pytest -m "unit or integration"

test-live:
> uv run pytest -m live --live

check: lint test

sync-docs:
> bin/sync-docs

# stub until T085
install:
> @echo "install: not implemented yet (see T085)"; exit 1
