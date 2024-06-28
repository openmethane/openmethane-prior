"""Open methane prior."""

import importlib.metadata

import dotenv

__version__ = importlib.metadata.version("openmethane_prior")


# Load environment variables from a local .env file
dotenv.load_dotenv()
