
# Adding sectors

To implement a new sector, a new PriorSector must be configured and added to
the `all_sectors` list in `src/openmethane_prior/sectors/__init__.py`.

## PriorSector

A PriorSector instance contains all the necessary functionality and metadata
for the sector to be computed and added to the output. Attributes are
documented in the source code, and the existing sectors provide many examples
of how these attributes can be configured.

### `create_estimate`

The most important component of PriorSector is the `create_estimate` method.
This will be called when constructing the prior, and the result will be added
to the output using a name derived from the PriorSector `name` attribute.

At a minimum, the `create_estimate` method should return a 2d gridded estimate
of methane emissions in kg / m^2 / s. Ideally, it includes a gridded estimate
for each daily timestep between the start date and end date in the config. If
a timestep is not included, the 2d gridded estimate will be automatically
duplicated for each day in the configured period.
