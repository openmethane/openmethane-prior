.PHONY: update-licenseheaders
update-licenseheaders:  ## add or update license headers in all python files
	licenseheaders --current-year --owner "The Superpower Institute Ltd" --projname "OpenMethane" --tmpl .copyright.tmpl --ext .py -x "venv/*"
