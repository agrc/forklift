# Changelog

### 9.4.0 (2021-09-08)

#### Features

- add sendgrid email option to config and messaging ([345](https://github.com/agrc/forklift/pull/345))

#### Bug Fixes

- include global id fields in hashing ([344](https://github.com/agrc/forklift/pull/344))
- preserve global id's in output ([342](https://github.com/agrc/forklift/pull/342))
- ignore the forklift hash field if it already exists ([343](https://github.com/agrc/forklift/pull/343))

### 9.3.0

#### Features

- add ability to send lift report to slack ([9123575](https://github.com/agrc/forklift/commit/912357556a4af30050ba41b4b77fc15294c06c91))
- add --profile switch to build command ([7dbbf3d](https://github.com/agrc/forklift/commit/7dbbf3d2106866e11b8c3dfe949af3f789857bb0))
- add `Pallet.process_on_fail` ([6354f54](https://github.com/agrc/forklift/commit/6354f5405f3d04bf865ece4788dbe779e9fd7ff8))
- add ability to ignore changes in requires processing ([0488862](https://github.com/agrc/forklift/commit/04888627c972639d84345f6ddf0e5d0509aa5bd2))
- add build cli command ([c66bbce](https://github.com/agrc/forklift/commit/c66bbcee9dcc3e8a79cbf3aa07af1f8a8d21f774))
- add changeDetectionTables config value and associated docs ([6cd30c9](https://github.com/agrc/forklift/commit/6cd30c93a98da4c8ac401012ab4b62272bf114d0))
- add check for Pro license and email on error ([b13ee91](https://github.com/agrc/forklift/commit/b13ee91dfc124f531ea03a0db890c21a7dd111ee)), closes [#312](https://github.com/agrc/forklift/issues/312)
- add machine name to global error email ([1dc7560](https://github.com/agrc/forklift/commit/1dc75609bc001e11966f8ccc8cff3dea43909d6e))
- add pallet arg to gift-wrap and tweak signature ([be80b99](https://github.com/agrc/forklift/commit/be80b999631fa1618c0c5e8aec9fb7550c044466)), closes [#307](https://github.com/agrc/forklift/issues/307)
- add server start/stop errors to ship reports ([4ce1bd8](https://github.com/agrc/forklift/commit/4ce1bd88f7b6423d5b582ffbd904deeeb7988955)), closes [#279](https://github.com/agrc/forklift/issues/279)
- allow configuration of the standalone logging level ([1aa61f8](https://github.com/agrc/forklift/commit/1aa61f87b206a464b3fe131caeab7a0c1944f9f8))
- add change detection implementation ([6644df8](https://github.com/agrc/forklift/commit/6644df8da4fbfbf0daefc47dffe6b3399d038b0a))
- log (debug) message when data is not found during build ([fcee3e0](https://github.com/agrc/forklift/commit/fcee3e0cdfb96d028e098d652273b96f1b7c37a4))
- post shipping report to slack ([f947f96](https://github.com/agrc/forklift/commit/f947f96831721c6fcad96a82d4387bb3251a65ba))
- raise custom exception rather than return None ([a0e6ecf](https://github.com/agrc/forklift/commit/a0e6ecf9b0f2f4c75af5a84be6a3d57562610b7e))

#### Bug Fixes

- allow for UNC pallet paths ([f2c69e4](https://github.com/agrc/forklift/commit/f2c69e402c746d1e8a220ce6cb12e397bf45fc22))
- create safe access middle man ([6526091](https://github.com/agrc/forklift/commit/6526091cb650e378a3b210f506f6cf24f8641d67))
- don't fix every source name ([2f6b32c](https://github.com/agrc/forklift/commit/2f6b32c8c87112b74c1cb2e61a16ec04191b39f6))
- explicitly specify no test for change detection append ([b435f11](https://github.com/agrc/forklift/commit/b435f116a2a2b1b857caf9993f9d73f3bfc8300a))
- fix bug preventing the detection of casing schema changes ([70be5a5](https://github.com/agrc/forklift/commit/70be5a5fedc62c40397804185ca04289faff83b8)), closes [#277](https://github.com/agrc/forklift/issues/277)
- fix mocked method name ([7ff5f87](https://github.com/agrc/forklift/commit/7ff5f87d5edfc55eb28ef74f491ebdc502cba355))
- handle errors posting report to slack ([fb7af5a](https://github.com/agrc/forklift/commit/fb7af5a77886ea5144ea1cb2d0eb70121fa7f3b9))
- handle mis-matching crates between pallet and packing list ([f8d853b](https://github.com/agrc/forklift/commit/f8d853b60e9bf545b438aee472886759d2f2e5a7))
- handle missing changeDetectionTables config value ([50913ba](https://github.com/agrc/forklift/commit/50913bafc49d82ecf9ffc6296d7d792607a40b99))
- handle more database sources name formats ([663fcc0](https://github.com/agrc/forklift/commit/663fcc0af2379764826ebb3d374699d5b6d0691a))
- fix int string concat ([e3158da](https://github.com/agrc/forklift/commit/e3158da29f6d20ebf0116fa3542a204bcc9e7f63))
- log actual services being shut down during gift-wrap ship ([dcabf4d](https://github.com/agrc/forklift/commit/dcabf4dc2129de3eb59239ae142381967785c2cf))
- make sure text is actually text ([d284f27](https://github.com/agrc/forklift/commit/d284f2738f3059af23df4b25bd1a4a8dc41987b4))
- method syntax ([c8bc253](https://github.com/agrc/forklift/commit/c8bc253ad112de5a3f0fb25c6184782d496f998a))
- prevent change detection from skipping initial data import ([14d7421](https://github.com/agrc/forklift/commit/14d7421eba2213d3f4fa391d1db70d09fa1759e2))
- stringify exception for crate exception message ([24f118e](https://github.com/agrc/forklift/commit/24f118eb1753cbdfee888c37ff8fc17b2a6720ef))
- **perf:** remove unnecessary call to exists ([85919f4](https://github.com/agrc/forklift/commit/85919f4ddd92460cbc73cbb5d9d3a43f86307923))
- make append more flexible with differing schemas ([3d76902](https://github.com/agrc/forklift/commit/3d769026d678a69acc0e207533b15733e43ccb5e)), closes [/github.com/agrc/forklift/blob/d442f7b7d866527ab886fbd2db82e1afa7af7072/src/forklift/core.py#L90](https://github.com/agrc//github.com/agrc/forklift/blob/d442f7b7d866527ab886fbd2db82e1afa7af7072/src/forklift/core.py/issues/L90)
- fix missing imports ([eb8fa51](https://github.com/agrc/forklift/commit/eb8fa51ad771585d8f1cc351d4329bf6ac8a5e65))
- remove duplicate check for pallet success ([3f8a5cd](https://github.com/agrc/forklift/commit/3f8a5cd17c3832220ed4e833a930be7c379d713a))
- remove the creation of "gift-wrapped" subfolder ([733af00](https://github.com/agrc/forklift/commit/733af000e9e53f55a9de3007458770dd6a27c1fa))
- show message and set default ([d4ca151](https://github.com/agrc/forklift/commit/d4ca15121ffd3133139d71073428ac0403640427))
- smarter skipping of shape, shape length and oid fields during compare ([552f04c](https://github.com/agrc/forklift/commit/552f04c2fafe671a614625b18a52d98af1b9b5bb))
- tweak slack ship report for server start/stop errors ([89abc68](https://github.com/agrc/forklift/commit/89abc68be1a38ac60aef24c61892c7da2788fda1))
- use geographic transformation environment in change detection ([d442f7b](https://github.com/agrc/forklift/commit/d442f7b7d866527ab886fbd2db82e1afa7af7072))
- **slack:** appended fields need to to_text ([987b97f](https://github.com/agrc/forklift/commit/987b97f845574b2557932b354f18d47d355ca3dc))
- use correct prop name for pallet result and message ([e91ed19](https://github.com/agrc/forklift/commit/e91ed1922bc5443466dfaad7bb2176cb4028710c))

### 9.2.1

#### bug fixes

- use status color for pallet message in ship report
- update ship report with correct pallet status

### 9.2.0

#### features

- allow shipping of pallets that did not lift all crates successfully #294
- replace flake8 and pep8 with pylint
- add init_standalone to allow pallets to be run more easily outside of forklift
- add packing slip to report email
- add forklift version to email

#### bug fixes

- disable ssl cert validation to gis servers
- show pallet import errors in report
- show git update errors in report
- apply create results to packing slip for use in ship
- show post_copy_process and ship times in ship report

### 9.1.0

- feat: allow for non github repos
- feat: create cli option for gift-wrapping data
- feat: implement special-delivery command lift
- docs: location for user install
- docs: markdown lint fixes
- fix: CVE-2018-18074 More information
- fix: return unhandled crate exceptions as strings
- fix: update version of pytest-cov
- fix: url creation based on shorthand
- fix: use PAT, dict syntax, and log repo name without token

### 9.0.1

- Better requests to ArcGIS Server and handling of errors.
- Docs: Better getting started steps.
- Removed multiprocess for git-update. Forklift was randomly hanging on git-update.
- Make default warehouse location consistent with other default paths.
- Account for `ERROR` result in crate report.
- Allow pallets that don't have any crates to copy data to dropoff by overriding `requires_processing`.

### 9.0.0

- Added `--send-emails` override option for both lift and ship commands.
- Added `ERROR` as a possible result type for crates.
- Removed unused crate property, `source_primary_key`
- BREAKING CHANGE: Split up lift and ship to be independent commands.
  - Replaced arcgis server env variables with config.json properties to allow for managing a silo'd architecture or multiple machines not in a cluster
  - Replaced env variables with config.json properties for consistency.
  - Ship now shuts down the entire ArcGIS Server machine rather than specific services. It also now does this one machine at time to minimize downtime.
  - Removed static data processing since it can now be accomplished by dropping the data into the dropoff folder.
- Removed tox because it's incompatible with conda.
- Enhanced the remove repo command to also delete the repository folder from disk ([#134](https://github.com/agrc/forklift/issues/134)).
- Removed the check for python version 3.
- Switched from nose to pytest for running tests.

### 8.5.0

- Add support for m & z values in the destination geometry ([#223](https://github.com/agrc/forklift/issues/223)).
- Add new crate warning type (`UPDATED_OR_CREATED_WITH_WARNINGS`) to address the [issue of processing crates with warnings](https://github.com/agrc/forklift/issues/#185). Now `WARNING` means there was a warning and the data was _not_ updated and `UPDATED_OR_CREATED_WITH_WARNINGS` means there was a warning and the data _was_ updated (or created).
- Add `Crate.was_updated()` method to save code in pallets when you want to check to see if the data for a crate was updated.

### 8.4.2

- Fix unicode bug with `-h` help CLI option.
- Fix bug in timeout code.
- Increase timeout value.
- Try to enforce running only on python 3.

### 8.4.1

- Add a timeout on http requests to avoid infinite hanging requests.

### 8.4.0

- Better management of parallel processes.
- Add process time per pallet to report ([#215](https://github.com/agrc/forklift/issues/215)).
- Implement `--skip-copy` parameter to `lift` allowing the user to skip copying data to `copyDestinations`.

### 8.3.1

- Fix bug in `list-pallets` command. Thanks [@joshgroeneveld](https://github.com/joshgroeneveld)!

### 8.3.0

- Parallelize the starting & stopping of ArcGIS Server services ([#118](https://github.com/agrc/forklift/issues/118)).
- Parallelize git_update ([#204](https://github.com/agrc/forklift/issues/204)).
- Fix the thin red line showing up at the top of successful report emails.
- Add warning to reports for duplicate features ([#185](https://github.com/agrc/forklift/issues/185)) and empty destinations ([#197](https://github.com/agrc/forklift/issues/197)).
- Give static copy errors their own line on the report.
- Add hostname to report email subject and body ([#182](https://github.com/agrc/forklift/issues/182)).

### 8.2.0

- Fixed a bug causing errors when trying to delete the scratch database [a6941b1ff3757267d69ec04cdf12488b1d77aa2c](https://github.com/agrc/forklift/commit/a6941b1ff3757267d69ec04cdf12488b1d77aa2c)
- Added a sample batch file ([`run_forklift.bat`](`run_forklift.bat`)) that can be used with Windows Scheduler.
- Fixed a bug caused by creating standalone tables with templates ([#197](https://github.com/agrc/forklift/issues/197)).
- Added the ability to update the ArcGIS Server credentials in [`LightSwitch`](src/forklift/arcgis.py) ([PR #200](https://github.com/agrc/forklift/pull/200)).

### 8.1.1

- Fixed bug that prevented pallets that through errors during `pallet.build()` from showing up in the report.
- Update tests and associated data for Pro 2.0.

### 8.1.0

- `Pallet.build` is now called on all pallets even when only a single pallet is run [#186](https://github.com/agrc/forklift/issues/186)
- `*.lock` files are ignored when copying from staging to `copy_data` destinations.
- Removed the deletion of the scratch GDB from the end of the forklift process. ArcGIS Pro was having issues with this and it's already being removed at the beginning of the process.

### 8.0.0

- Upgraded to python 3.5. Now requires running from within the [ArcGIS Pro Conda environment](http://pro.arcgis.com/en/pro-app/arcpy/get-started/using-conda-with-arcgis-pro.htm) ([PR #187](https://github.com/agrc/forklift/pull/187)).
