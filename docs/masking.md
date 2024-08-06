
# Masking data

In data science, masking is the process of subsetting or excluding spatial data
based on underlying properties.

The most common type of masking in Open Methane is applying a "land mask",
which is a binary field that describes whether each grid cell covers "land" or
"sea". In reality, many grid cells may contain both land and sea, but will the
land mask classify each cell as 100% land or 100% sea due to its binary nature.

## Land masking a spatial proxy

Many sectoral layers in the prior are created by starting with a national total
for that sector, and using a spatial proxy to determine how to distribute those
emissions across Australia. Sectors which are generated this way include:

- agriculture
- lulucf
- waste
- industrial
- stationary
- transport

The activities in these sectors that emit methane are entirely land-based.
However, the spatial proxies we use to distribute the emissions, such as the
NASA night lights TIFF, may have some values over water. We want to avoid
attributing emissions to a cell that is classified as "sea", as this is likely
to be a mistake.

For these sectors, we apply the landmask to the source dataset before
allocating emissions. This ensures that 100% of the inventory emissions are
allocated to cells within our domain.

## Land masking a coarse dataset

Some sectoral estimates are taken directly from previous studies/datasets that
have already been spatialised on a grid. These are prepared by regridding the
source dataset onto the target domain grid. When the source dataset uses
similar cell size or smaller, we can usually trust that the emissions we
aggregate into each cell are fine to leave as is.

However, when the source grid is quite coarse (cells that are larger than the
target grid), grid cells which sit partially over water may be made up of
cells in the target grid where only a small number are over land. Sectors with
coarse grids include:
- termites
- wetlands

Our current approach for these sectors is to apply the land mask to results
after regridding, so that cells over water do record methane emission where
it's very unlikely. This has a downside that some real emissions may be "lost",
as all the emissions that occur within that large grid cell probably occur in
the parts of it that are over land.

A smarter approach, which we may pursue in the future, would be to take the
entire emission estimate from the source grid cell, and allocate it only to
target grid cells which intersect with the source cell and are not over water.
