.PHONY: test lint format playground run server sync

sync:
	uv sync --dev

test:
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

server:
	uv run uvicorn app.server:api_app --host 127.0.0.1 --port 8000 --reload

playground:
	uv run adk web . --port 8501

run:
	uv run adk run app
