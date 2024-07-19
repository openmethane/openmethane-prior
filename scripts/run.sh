#!/usr/bin/env bash
# End-to-end script to run the prior
#
# This is assumed to run from the root directory.
# Any existing environment variables will override the values from the `.env` files
#

set -Eeuo pipefail
set -x

if [[ ! -f .env ]]; then
  echo "No .env file found. Copying .env.example to .env"
  cp .env.example .env
fi

export START_DATE=${START_DATE:-2022-07-22}
export END_DATE=${END_DATE:-2022-07-22}

echo "Download static inputs"
python scripts/omDownloadInputs.py

echo "Preparing the prior"
python scripts/omPrior.py --start-date $START_DATE --end-date $END_DATE

