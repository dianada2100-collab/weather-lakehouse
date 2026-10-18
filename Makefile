.PHONY: install test run-local run-aws clean

install:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

test:
	python3 -m pytest -v

run-local:
	PYTHONPATH=src python3 -m weather_pipeline.run --start 2025-01-01 --end 2025-01-07

run-aws:
	PYTHONPATH=src STORAGE_BACKEND=s3 python3 -m weather_pipeline.run

clean:
	rm -rf data .pytest_cache
