
# Diagnostic notebooks

Notebooks are a good way to capture frequently used diagnostics and rapidly
prototype data exploration.

## Running Jupyter

Jupyter can be opened locally with poetry:

```shell
poetry run jupyter notebook
```

## Jupytext

Notebooks in this folder should be written as plain .py files, and opened in
Jupyter as Jupytext. Once Jupyter is running:
- find the relevant .py file in `notebooks`
- right-click the .py file and select Open With -> Jupytext Notebook

If you make changes to the notebook file in your IDE, you will need to reload
the file in Jupyter with:
- File -> Reload Python File from Disk

If you make changes to any modules that are used by the notebook, the Jupyter
kernel will need to be restarted. You can restart the kernel and run all cells
or run to a selected cell with:
- Kernel -> Restart Kernel and Run up to Selected Cell, or
- Kernel -> Restart Kernel and Run All Cells...
