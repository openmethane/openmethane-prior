.PHONY: update-licenseheaders
update-licenseheaders:  ## add or update license headers in all python files
	licenseheaders -y 2023 --owner "The Superpower Institute Ltd" --projname "OpenMethane" --tmpl .copyright.tmpl --ext .py -x "venv/*"

.PHONY: build
build:  ## Build the docker container locally
	docker build --platform=linux/amd64 -t openmethane-prior .

.PHONY: virtual-environment
virtual-environment:  ## update virtual environment, create a new one if it doesn't already exist
	poetry lock --no-update
	# Put virtual environments in the project
	poetry config virtualenvs.in-project true
	poetry install --all-extras
	# TODO: Add last line back in when pre-commit is set up
	# poetry run pre-commit install

.PHONY: clean
clean:  ## remove generated temporary files
	find intermediates outputs inputs/om-domain-info.nc -type f ! -name 'README.md' -delete

.PHONY: clean-all
clean-all:  ## remove all temporary files including downloaded data
	find inputs intermediates outputs -type f ! -name 'README.md' -delete

.PHONY: download
download: ## Download the data for the project
	poetry run python scripts/omDownloadInputs.py

.PHONY: run
run:  download ## Run the project for an example period
	poetry run python scripts/omCreateDomainInfo.py
	poetry run python scripts/omPrior.py 2022-07-01 2022-07-01

.PHONY: ruff-fixes
ruff-fixes:  # Run ruff on the project
 	# Run the formatting first to ensure that is applied even if the checks fail
	poetry run ruff format .
	poetry run ruff check --fix .
	poetry run ruff format .

.PHONY: test
test:  ## Run the tests
	poetry run python -m pytest -r a -v tests