🚜 Forklift
===================================

[![Build Status](https://travis-ci.org/agrc/forklift.svg?branch=master)](https://travis-ci.org/agrc/forklift) [![codecov.io](http://codecov.io/github/agrc/forklift/coverage.svg?branch=master)](http://codecov.io/github/agrc/forklift?branch=master)

A CLI tool for managing a plethora of scheduled task python scripts.

### Development Usage
1. setup.py install
1. Update `secrets.py` based on the [sample.](/src/forklift/secrets_sample.py)
1. from the `**/src**` directory execute `python -m forklift -h` for usage.

### Tests
`tox`

Tests that depend on a local SDE database (see `tests/data/UPDATE_TESTS.bak`) will automatically be skipped if it is not found on your system.
