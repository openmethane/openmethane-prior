# OpenMethane prior emissions estimate

Method to calculate a gridded, prior emissions estimate for methane across Australia.

This repository is shipped with sample input data in the `inputs` so that it will run out of the box.

## Initialise

Run

```console
pip install -r requirements.txt
```

Copy the `.env.example` file to `.env` and customise the paths as you need. The example file refers to the sample inputs shipped in the `inputs` folder.

## Run

To calculate emissions for all layers, run:

```console
python omPrior.py
```

To skip re-projecting raster layers (you only need to do this once for every time you change the input file), add the `--skip-reproject` option.

## Outputs

Outputs can be found in the `outputs` folder. The emissions layers will be written as variables to a copy of the input domain file, with an `OCH4_` prefix for the methane layer variable names. The sum of all layers will be sotred in the `OCH4_TOTAL` layer.

The name of the layered output file will be `om-{INPUT_DOMAIN_FILENAME}`.

The output folder will also contain any re-projected raster data.
