#!/bin/bash

# This script needs to be sourced

# Create the python virtual environment
python3 -m venv .venv

# Activate the environment
. .venv/bin/activate

# Install packages
python3 -m pip install numpy
python3 -m pip install pyyaml
python3 -m pip install XlsxWriter
python3 -m pip install plotly
python3 -m pip install kaleido
python3 -m pip install pandas
