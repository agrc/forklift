🚜📦✨ forklift
===================================
A python CLI tool for managing and organizing the repetitive tasks involved with keeping remote geodatabases in sync with their sources. In other words, it is a tool to tame your scheduled task nightmare.

#### Rules

> The first rule of :tractor: is it does not work on any sabbath.

> The second rule of :tractor: is that it's out of your element Donny.

## Usage

The work that forklift does is defined by [Pallets](src/forklift/models.py). `forklift.models.Pallet` is a base class that allows the user to define a job for forklift to perform by creating a new class that inherits from `Pallet`. Each pallet should have `Pallet` in it's file name and be unique from it's other pallets.

A Pallet can have zero or more [Crates](src/forklift/models.py). `forklift.models.Crate` is a class that defines data that needs to be moved from one location to another (reprojecting to web mercator by default). Crates are created by calling the `add_crates` (or `add_crate`) methods within the `build` method on the pallet. For example:

```python
class MyPallet(Pallet):
    def __init__(self):
        #: this is required to initialize the Pallet base class properties
        super(MyPallet, self).__init__()

    def build(self, configuration)
        #: all operations that can throw an exception should be done in build
        destination_workspace = 'C:\\MapData'
        source_workspace = path.join(self.garage, 'connection.sde')

        self.add_crate('Counties', {'source_workspace': source_workspace,
                                    'destination_workspace': destination_workspace})
```

For details on all of the members of the `Pallet` and `Crate` classes see [models.py](src/forklift/models.py).

For examples of pallets see [samples/PalletSamples.py](samples/PalletSamples.py).

#### CLI

Interacting with forklift is done via the [command line interface](src/forklift/cli.py). Run `forklift -h` for a list of all of the available commands.

#### Config File Properties

`config.json` is created in the working directory after running `forklift config init`. It contains the following properties:

- `warehouse` The folder location where all of the `repositories` will be cloned into and where forklift will scan for pallets to lift.
- `repositories` A list of github repositories in the `<owner>/<name>` format that will be cloned/updated into the `warehouse` folder.
- `stagingDestination` The folder location where forklift creates and manages data before being copied to `copyDestinations`. This allows data in "production" to not be affected while forklift is running and if there are any issues. Data will only be copied if all crates are processed successfully. This is a helper method for creating crates. Usage would be from within a Pallet: `os.path.join(self.staging_rack, 'the.gdb')`
- `copyDestinations` An array of folder locations that forklift will  copy data to. This is the "production" drop off location. The data is defined in `Pallet.copy_data` and is copied upon successful processing of the pallet.
- `configuration` A configuration string (`Production`, `Staging`, or `Dev`) that is passed to `Pallet:build` to allow a pallet to use different settings based on how forklift is being run. Defaults to `Production`.
- `sendEmails` A boolean value that determines whether or not to send forklift summary report emails after each lift.
- `notify` An array of emails that will be sent the summary report each time `forklift lift` is run.

Any of these properties can be set via the `config set` command like so:
```
forklift config set --key sendEmails --value False
```
If the property is a list then the value is appended to the existing list.

## Install to First Successful Run

From within the [ArcGIS Pro conda environment](http://pro.arcgis.com/en/pro-app/arcpy/get-started/using-conda-with-arcgis-pro.htm) (`c:\Program Files\ArcGIS\Pro\bin\Python\scripts\proenv.bat`):
1. Install [git](https://git-scm.com/)
1. `pip install .\` from the directory containing `setup.py`.
1. `forklift config init`
1. `forklift config set --key copyDestinations --value c:\\MapData` - This is where you want your output placed.
1. `forklift repos --add agrc/parcels` - The agrc/parcels is the user/repo to scan for Pallets.
1. `forklift garage open` - Add all connection.sde files to the forklift garage.
1. Set the following **user** environmental variables.
  - _required for sending email reports and/or starting/stopping ArcGIS Server Services_
  - _may require a reboot_
    - `FORKLIFT_SMTP_SERVER` The SMTP server that you want to send emails with.
    - `FORKLIFT_SMTP_PORT` The SMTP port number.
    - `FORKLIFT_FROM_ADDRESS` The from email address for emails sent by forklift.
    - `FORKLIFT_POOL_PROCESSES` (optional: defaults to 20) Number of [multiprocessing processes](https://docs.python.org/3/library/multiprocessing.html#using-a-pool-of-workers) to be used to parallelize the starting and stopping of services.
1. Edit the `config.json` to add the arcgis server(s) to manage. The options property will be mixed in to all of the other servers.
    - `username` ArcGIS admin username.
    - `password` ArcGIS admin password.
    - `host` ArcGIS host address eg: `localhost`
    - `port` ArcGIS server instance port eg: 6080
```json
"servers": {
   "options": {
       "username": "mapserv",
       "password": "test",
       "port": 6080
   },
   "primary": {
       "host": "localhost",
   },
   "secondary": {
       "host": "127.0.0.1"
   },
   "backup": {
       "host": "0.0.0.0",
       "username": "test",
       "password": "password",
       "port": 6443
   }
}
```
1. `forklift lift`

`run_forklift.bat` is an example of a batch file that could be used to run forklift via Window Scheduler.


#### Development Usage

- create new env
  - `conda create --name forklift --clone arcgispro-py3`
  - `activate forklift`
- install deps
  - `conda install flake8 mock`
  - `pip install nose-cov rednose`
- optionally install forklift
  - `cd forklift`
  - `pip install .\ -U`
- run forklift
  - for the installed version execute `forklift -h`
  - for the source version, from the `**/src**` directory, execute `python -m forklift -h` for usage

#### Tests

##### On first run
- install deps
  - `conda install flake8 mock`
  - `pip install nose-cov rednose`
- run tests
  - `nosetests --with-id --rednose --cov-config .coveragerc --with-coverage --cover-package forklift --cov-report term-missing --cover-erase`

##### On subsequent runs
`nosetests --with-id --rednose --cov-config .coveragerc --with-coverage --cover-package forklift --cov-report term-missing --cover-erase`

_Tests that depend on a local SDE database (see `tests/data/UPDATE_TESTS.bak`) will automatically be skipped if it is not found on your system._

#### Linting
`flake8 src/forklift tests`

# Changelog

**8.5.0**
- Add support for m & z values in the destination geometry ([#223](https://github.com/agrc/forklift/issues/223)).
- Add new crate warning type (`UPDATED_OR_CREATED_WITH_WARNINGS`) to address the [issue of processing crates with warnings](https://github.com/agrc/forklift/issues/#185). Now `WARNING` means there was a warning and the data was _not_ updated and `UPDATED_OR_CREATED_WITH_WARNINGS` means there was a warning and the data _was_ updated (or created).
- Add `Crate.was_updated()` method to save code in pallets when you want to check to see if the data for a crate was updated.

**8.4.2**
- Fix unicode bug with `-h` help CLI option.
- Fix bug in timeout code.
- Increase timeout value.
- Try to enforce running only on python 3.

**8.4.1**
- Add a timeout on http requests to avoid infinite hanging requests.

**8.4.0**
- Better management of parallel processes.
- Add process time per pallet to report ([#215](https://github.com/agrc/forklift/issues/215)).
- Implement `--skip-copy` parameter to `lift` allowing the user to skip copying data to `copyDestinations`.

**8.3.1**
- Fix bug in `list-pallets` command. Thanks [@joshgroeneveld](https://github.com/joshgroeneveld)!

**8.3.0**
- Parallelize the starting & stopping of ArcGIS Server services ([#118](https://github.com/agrc/forklift/issues/118)).
- Parallelize git_update ([#204](https://github.com/agrc/forklift/issues/204)).
- Fix the thin red line showing up at the top of successful report emails.
- Add warning to reports for duplicate features ([#185](https://github.com/agrc/forklift/issues/185)) and empty destinations ([#197](https://github.com/agrc/forklift/issues/197)).
- Give static copy errors their own line on the report.
- Add hostname to report email subject and body ([#182](https://github.com/agrc/forklift/issues/182)).

**8.2.0**
- Fixed a bug causing errors when trying to delete the scratch database [a6941b1ff3757267d69ec04cdf12488b1d77aa2c](https://github.com/agrc/forklift/commit/a6941b1ff3757267d69ec04cdf12488b1d77aa2c)
- Added a sample batch file ([`run_forklift.bat`](`run_forklift.bat`)) that can be used with Windows Scheduler.
- Fixed a bug caused by creating standalone tables with templates ([#197](https://github.com/agrc/forklift/issues/197)).
- Added the ability to update the ArcGIS Server credentials in [`LightSwitch`](src/forklift/arcgis.py) ([PR #200](https://github.com/agrc/forklift/pull/200)).

**8.1.1**
- Fixed bug that prevented pallets that through errors during `pallet.build()` from showing up in the report.
- Update tests and associated data for Pro 2.0.

**8.1.0**
- `Pallet.build` is now called on all pallets even when only a single pallet is run [#186](https://github.com/agrc/forklift/issues/186)
- `*.lock` files are ignored when copying from staging to `copy_data` destinations.
- Removed the deletion of the scratch GDB from the end of the forklift process. ArcGIS Pro was having issues with this and it's already being removed at the beginning of the process.

**8.0.0**
- Upgraded to python 3.5. Now requires running from within the [ArcGIS Pro Conda environment](http://pro.arcgis.com/en/pro-app/arcpy/get-started/using-conda-with-arcgis-pro.htm) ([PR #187](https://github.com/agrc/forklift/pull/187)).
