.PHONY: update-licenseheaders
update-licenseheaders:  ## add or update license headers in all python files
	uv tool run licenseheaders \
		--years "2023-2025" --owner "The Superpower Institute Ltd" --projname "Open Methane" \
		--tmpl .copyright.tmpl --ext .py \
		-x "venv/*" -x "tests/*"

.PHONY: install
install:  ## install or update dependencies, creating a virtual env if one doesn't exist
	uv sync

.PHONY: clean
clean:  ## remove generated temporary files
	find data/intermediates data/outputs -type f -delete

.PHONY: clean-all
clean-all:  ## remove all temporary files including downloaded data
	rm -r data

.PHONY: run-example
run-example:  ## Run the project for an example period
	uv run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01

.PHONY: format
format:  # Run ruff on the project
	uv format

.PHONY: test
test:  ## Run the tests
	uv run python -m pytest -r a -v tests

.PHONY: build
build:  ## Build the docker container locally
	docker build --platform=linux/amd64 -t openmethane-prior .

.PHONY: start
start: build  ## Start the docker container locally
	docker run --rm -it \
		-v ~/.cdsapirc:/home/app/.cdsapirc \
		-v $(PWD):/opt/project \
		-v /opt/project/.venv \
		openmethane-prior

.PHONY: run
run: build clean  ## Run the prior in the docker container
	# This requires a valid `~/.cdsapirc` file
	docker run --rm -it \
		-v ~/.cdsapirc:/home/app/.cdsapirc \
		-v $(PWD):/opt/project \
		-v /opt/project/.venv \
		openmethane-prior \
		python scripts/omPrior.py --start-date 2022-07-22 --end-date 2022-07-22
