
# Oil and Gas Sector

The oil and gas sector is the most complicated sector implementation in the
Australia prior. There's no pre-existing high quality dataset that can be
used to both locate and scale emission sources from the sector, and no clear
spatial proxy.

Oil and gas extraction occurs in "fields" of wells or bores, somtimes located
offshore. Extracted resources are transported through pipelines to various
pieces of infrastructure to be compressed or combined, and eventually to
refinery facilities. Methane can be lost to the atmosphere for various reasons
at any of these locations, resulting in physically dispersed infrastructure
which is not well documented by the private companies which operate it.

## Methodology

Emissions are likely to occur in three possible parts of the oil and gas
infrastructure:
- wells or boreholes where oil or gas are extracted
- processing facilities
- pipelines connecting wells and other infrastructure

### Wells and boreholes

#### Locations

Oil and gas extraction are covered by petroleum mining laws in Australia, and
most Australian states provide public datasets of petroleum mining titles
(aka leases/licenses/tenements). Some states also provide public datasets
of drill/bore/well locations.

Drillhole datasets typically include enough detail to determine which bores
or wells are used for petroleum production, giving us precise locations for
emission sources.

#### Activity period

Drillhole datasets typically include the approximate date a bore was drilled
(sometimes just the year), but don't include the date a bore was capped or
depleted. Although some bore datasets do include the bore status, ie CAPPED,
this is the status **at the time the dataset was last updated**, and not
necessarily the status in the period of interest for the prior.

We use a very rough method to determine whether a single bore may have been
producing emissions during a target period (`start_date` to `end_date`).
- if the bore drill date is later than `end_date`, no emissions are possible
- correlate the bore coordinates with all petroleum production titles it
  is contained by
- if the range from `start_date` to `end_date` overlaps with the range from
  title grant date to title expiry date, emissions are possible

This method has obvious problems:

1. emissions are unlikely to start immediately after drilling, however without
   a more accurate start date, this is at least a lower bound
2. most bores/wells will be depleted or capped well before the petroleum title
   expires, however without an accurate capping date, this is at least an upper
   bound.
3. there is potentially a long period (years) where an entire field / title
   has stopped producing, but the title is still active.

On a coarse grid such as our 10x10km grid, 1. and 2. probably aren't serious,
because emissions will be dispersed amongst a number of points within each grid
cell.

The biggest issue is 3., as it will place emissions in some fields, possibly
for years after production has ceased. Assuming that capped wells don't
continue to emit methane, this will misallocate potentially significant
emissions. Unfortunately we currently don't have a better solution.

### Processing facilities

Not yet implemented.

### Pipelines

Public datasets do exist which record the shape and status of oil and gas
pipelines in Australia, however there are several issues using these shape
files to estimate emissions.

1. Lack of temporal data

Pipeline datasets list the current status of pipelines, but don't necessarily
include the dates pipelines actually began operating.

2. Lack of leakage estimates

We're not currently aware of any research or data on how much methane leaks
from pipelines, or where leakage occurs. This makes it hard to attribute a
specific volume of emission to specific locations along any given pipeline.

For now, pipelines are not included in our bottom up estimate. If better data
or research becomes available in the future, this would be a welcome addition.