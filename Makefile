.PHONY: install pipeline test validate all

install:
	python -m pip install -r requirements.txt

pipeline:
	PYTHONPATH=Python/src python -m ecom_opt.run_pipeline

test:
	PYTHONPATH=Python/src pytest -q

validate: pipeline test

all: validate
