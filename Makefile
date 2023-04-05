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
	find . -name '*.mo' -exec rm -f {} +
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
	rm -f .coverage*
	rm -fr htmlcov/
	rm -fr .pytest_cache/

.PHONY: clean-docs
clean-docs: ## remove docs build artifacts
	-$(MAKE) -C docs clean
	rm -fr docs/api/
	rm -f docs/*.md

.PHONY: reuse
reuse: dist ## check with self
	poetry run reuse lint
	tar -xf dist/reuse*.tar.gz -C dist/
	# This prevents the linter from using the project root as root.
	git init dist/reuse*/
	poetry run reuse --root dist/reuse*/ lint

.PHONY: docs
docs: ## generate Sphinx HTML documentation, including API docs
	poetry export --with dev --without-hashes >docs/requirements.txt
	$(MAKE) -C docs html

.PHONY: docs-ci
docs-ci: ## generate Sphinx HTML documentation, including API docs without dependency file generation (for CI)
	$(MAKE) -C docs html

.PHONY: dist
dist: clean-build clean-pyc clean-docs ## builds source and wheel package
	poetry build
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
test-release: ## package and upload to testpypi
	poetry config repositories.test-pypi https://test.pypi.org/legacy/
	# You may need to use `poetry config pypi-token.test-pypi pypi-YYYYYYYY`
	poetry publish --build -r test-pypi

.PHONY: release
release: ## package and upload a release
	# You may need to use `poetry config pypi-token.pypi pypi-YYYYYYYY`
	poetry publish --build

.PHONY: update-resources
update-resources: ## update spdx data files
	python .github/workflows/license_list_up_to_date.py --download
