.DEFAULT_GOAL := build
.PHONY: build publish package coverage test lint docs venv
PROJ_SLUG = zenml
CLI_NAME = zenml
PY_VERSION = 3.6
LINTER = pylint


build:
	pip install --editable .

run:
	$(CLI_NAME) run

submit:
	$(CLI_NAME) submit

freeze:
	pip freeze > requirements.txt

lint:
	$(LINTER) $(PROJ_SLUG)

test: lint
	py.test --cov-report term --cov=$(PROJ_SLUG) tests/

quicktest:
	py.test --cov-report term --cov=$(PROJ_SLUG) tests/

coverage: lint
	py.test --cov-report html --cov=$(PROJ_SLUG) tests/

docs: coverage
	mkdir -p docs/source/_static
	mkdir -p docs/source/_templates
	cd docs && $(MAKE) html

answers:
	cd docs && $(MAKE) html
	xdg-open docs/build/html/index.html

package: clean
	python setup.py sdist

publish: package
	twine upload dist/*

clean:
	rm -rf dist \
	rm -rf docs/build \
	rm -rf *.egg-info

venv :
	virtualenv --python python$(PY_VERSION) venv

install:
	pip install -r requirements.txt

licenses:
	pip-licenses --with-url --format=rst \
	--ignore-packages $(shell cat .pip-license-ignore | awk '{$$1=$$1};1')
