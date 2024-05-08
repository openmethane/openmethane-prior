.PHONY: update-licenseheaders
update-licenseheaders:  ## add or update license headers in all python files
	licenseheaders -y 2023 --owner "The Superpower Institute Ltd" --projname "OpenMethane" --tmpl .copyright.tmpl --ext .py -x "venv/*"
