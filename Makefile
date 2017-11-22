.DEFAULT_GOAL := help

.PHONY: help
help: ## show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: clean
clean: clean-build clean-pyc clean-test clean-docs ## remove all build, test, coverage and Python artifacts

.PHONY: clean-build
clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .cache/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

.PHONY: clean-pyc
clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

.PHONY: clean-docs
clean-docs: ## remove docs build artifacts
	-$(MAKE) -C docs clean
	rm -f docs/en_pyssant*.rst
	rm -f docs/modules.rst
	rm -f docs/history.rst
	rm -f docs/readme.md

.PHONY: lint
lint: ## check style with pylint
	pylint src/reuse tests/*.py

.PHONY: test
test: ## run tests quickly
	py.test

.PHONY: coverage
coverage: ## check code coverage quickly
	py.test --cov-report term-missing --cov=src/reuse

.PHONY: docs
docs: clean-docs ## generate Sphinx HTML documentation, including API docs
	sphinx-apidoc --separate -o docs/ src/reuse
	changelogdir -o docs/history.rst
	cp README.md docs/readme.md  # Because markdown cannot include...
	$(MAKE) -C docs html

.PHONY: tox
tox: ## run all tests against multiple versions of Python
	tox

.PHONY: dist
dist: clean docs ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

.PHONY: test-release
test-release: dist  ## package and upload to testpypi
	twine upload -r testpypi dist/*

.PHONY: release
release: dist  ## package and upload a release
	twine upload -r pypi dist/*

.PHONY: develop
develop: ## set up virtualenv for development
	pip install -r requirements.txt
	REUSE_DEV=1 python setup.py develop
