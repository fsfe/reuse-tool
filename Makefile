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

.PHONY: clean-docs
clean-docs: ## remove docs build artifacts
	-$(MAKE) -C docs clean
	rm -f docs/en_pyssant*.rst
	rm -f docs/modules.rst
	rm -f docs/history.md
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
	cp README.md docs/readme.md  # Because markdown cannot include...
	cp CHANGELOG.md docs/history.md
	$(MAKE) -C docs html

.PHONY: tox
tox: ## run all tests against multiple versions of Python
	tox

.PHONY: dist
dist: clean docs compile-mo ## builds source and wheel package
	RST_ERROR=1 python setup.py sdist
	RST_ERROR=1 python setup.py bdist_wheel
	ls -l dist

.PHONY: create-pot
create-pot:  ## generate .pot file
	xgettext --add-comments --output=po/reuse.pot --files-from=po/POTFILES.in
	xgettext --add-comments --output=po/argparse.pot /usr/lib*/python3*/argparse.py
	msgcat --output=po/reuse.pot po/reuse.pot po/argparse.pot

.PHONY: update-po-files
update-po-files: create-pot  ## update .po files
	find ./po -name "*.po" -exec msgmerge --width=79 --output={} {} po/reuse.pot \;

.PHONY: compile-mo
compile-mo:  ## compile .mo files
	find ./po -name "*.po" | while read f; do msgfmt $$f -o $${f%.po}.mo; done

.PHONY: test-release
test-release: dist  ## package and upload to testpypi
	twine upload --sign -r testpypi dist/*

.PHONY: release
release: dist  ## package and upload a release
	twine upload --sign -r pypi dist/*

.PHONY: install-requirements
install-requirements:  ## install requirements
	pip install -r requirements.txt

.PHONY: uninstall
uninstall:  ## uninstall reuse
	-pip uninstall -y fsfe-reuse

.PHONY: install
install: uninstall install-requirements dist  ## install reuse
	pip install dist/*.whl

.PHONY: develop
develop: uninstall install-requirements  ## install source directory
	REUSE_DEV=1 python setup.py develop
