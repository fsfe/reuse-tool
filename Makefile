# SPDX-FileCopyrightText: 2017 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

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
	rm -fr pip-wheel-metadata/
	find ./po -name '*.mo' -exec rm -f {} +
	find ./po -name '*.pot' -exec rm -f {} +
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

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
	rm -fr .pytest_cache/

.PHONY: clean-docs
clean-docs: ## remove docs build artifacts
	-$(MAKE) -C docs clean
	rm -fr docs/api/
	rm -f docs/*.md

.PHONY: lint
lint: ## check with pylint
	pylint src/reuse tests/*.py

.PHONY: blackcheck
blackcheck: ## check with black
	black --check .

.PHONY: black
black: ## format with black
	isort -y -s build -s dist
	black .

.PHONY: reuse
reuse: dist ## check with self
	reuse lint
	tar -xf dist/reuse*.tar.gz -C dist/
	# This prevents the linter from using the project root as root.
	git init dist/reuse*/
	cd dist/reuse*/; reuse lint

.PHONY: test
test: ## run tests quickly
	py.test

.PHONY: coverage
coverage: ## check code coverage quickly
	py.test --cov-report term-missing --cov=src/reuse

.PHONY: docs
docs: ## generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs html

.PHONY: tox
tox: ## run all tests against multiple versions of Python
	tox

.PHONY: dist
dist: clean-build clean-pyc clean-docs ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

.PHONY: create-pot
create-pot:  ## generate .pot file
	xgettext --add-comments --from-code=utf-8 --output=po/reuse.pot --files-from=po/POTFILES.in
	xgettext --add-comments --output=po/argparse.pot /usr/lib*/python3*/argparse.py
	msgcat --output=po/reuse.pot po/reuse.pot po/argparse.pot

.PHONY: update-po-files
update-po-files: create-pot  ## update .po files
	find ./po -name "*.po" -exec msgmerge --width=79 --output={} {} po/reuse.pot \;

.PHONY: test-release
test-release: dist  ## package and upload to testpypi
	twine upload --sign -r testpypi dist/*

.PHONY: release
release: dist  ## package and upload a release
	twine upload --sign -r pypi dist/*

.PHONY: install-requirements
install-requirements:  ## install requirements
	pip install -r requirements.txt

.PHONY: install-dev-requirements
install-dev-requirements: install-requirements  ## install dev requirements
	pip install -r requirements-dev.txt

.PHONY: uninstall
uninstall:  ## uninstall reuse
	-pip uninstall -y reuse

.PHONY: install
install: uninstall install-requirements  ## install reuse
	python setup.py install

.PHONY: update-resources
update-resources:  ## update spdx data files
	curl https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json \
		> src/reuse/resources/licenses.json
	curl https://raw.githubusercontent.com/spdx/license-list-data/master/json/exceptions.json \
		> src/reuse/resources/exceptions.json

.PHONY: develop
develop: uninstall install-dev-requirements  ## install source directory
	pre-commit install
	python setup.py develop
