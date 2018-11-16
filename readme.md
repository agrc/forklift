# 🚜📦✨ forklift

A python CLI tool for managing and organizing the repetitive tasks involved with keeping remote geodatabases in sync with their sources. In other words, it is a tool to tame your scheduled task nightmare.

![basically forklift](https://user-images.githubusercontent.com/325813/46423176-3bf40300-c6f3-11e8-9ab6-32d78edca9e6.png)

<https://xkcd.com/2054/>

## Rules

> The first rule of :tractor: is it does not work on any sabbath.
>
> The second rule of :tractor: is that it's out of your element Donny.

## Usage

The work that forklift does is defined by [Pallets](src/forklift/models.py). `forklift.models.Pallet` is a base class that allows the user to define a job for forklift to perform by creating a new class that inherits from `Pallet`. Each pallet should have `Pallet` in it's file name and be unique among other pallets run by forklift.

A Pallet can have zero or more [Crates](src/forklift/models.py). `forklift.models.Crate` is a class that defines data that will be moved from one location to another (reprojecting to web mercator by default). Crates are created by calling the `add_crates` (or `add_crate`) methods within the `build` method on the pallet. For example:

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

### CLI

Interacting with forklift is done via the [command line interface](src/forklift/__main__.py). Run `forklift -h` for a list of all of the available commands.

### Config File Properties

`config.json` is created in the working directory after running `forklift config init`. It contains the following properties:

- `configuration` - A configuration string (`Production`, `Staging`, or `Dev`) that is passed to `Pallet:build` to allow a pallet to use different settings based on how forklift is being run. Defaults to `Production`.
- `dropoffLocation` - The folder location where production ready files will be placed. This data will be compressed and will not contain any forklift artifacts. Pallets place their data in this location within their `copy_data` property.
- `email` - An object containing `fromAddress`, `smptPort`, and `smtpServer` for sending report emails.
- `hashLocation` - The folder location where forklift creates and manages data. This data contains hash digests that are used to check for changes. Referencing this location within a pallet is done by: `os.path.join(self.staging_rack, 'the.gdb')`.
- `notify` - An array of emails that will be sent the summary report each time `forklift lift` is run.
- `poolProcesses` - The number of parallel processes forklift will use when git cloning/pulling repositories.
- `repositories` - A list of github repositories in the `<owner>/<name>` format that will be cloned/updated into the `warehouse` folder.
- `sendEmails` - A boolean value that determines whether or not to send forklift summary report emails after each lift.
- `servers` - An object describing one or more production servers that data will be shipped to. See below for more information.
- `serverStartWaitSeconds` - The number of seconds that forklift will wait after starting ArcGIS Server. Defaults to 300 (5 minutes).
- `shipTo` - A folder location that forklift will copy data to for each server. This is the datas' final location. Everything in the `dropoffLocation` will be copied to the `shipTo` location during a forklift ship. The `shipTo` path is optionally formatted with the `servers.host` value if present and necessary. Place a `{}` in your `shipTo` path if you would like to use this feature. eg: `\\\\{}\\c$\\data`.
- `warehouse` - The folder location where all of the `repositories` will be cloned into and where forklift will scan for pallets to lift.

Any of these properties can be set via the `config set` command like so:

```shell
forklift config set --key sendEmails --value False
```

If the property is a list then the value is appended to the existing list.

### Install to First Successful Run

From within the [ArcGIS Pro conda environment](http://pro.arcgis.com/en/pro-app/arcpy/get-started/using-conda-with-arcgis-pro.htm) (`c:\Program Files\ArcGIS\Pro\bin\Python\scripts\proenv.bat`):

1. Install [git](https://git-scm.com/).
1. Install [ArcGIS Pro](https://pro.arcgis.com/en/pro-app/).
1. Add ArcGIS Pro to your path `c:\Program Files\ArcGIS\Pro\bin\Python\scripts\`.
1. Create a conda environment for forklift `conda create --name forklift --clone arcgispro-py3`.
1. Activate the conda environment `activate forklift`.
1. `pip install .\` from the directory containing `setup.py`.
1. Install the python dependencies for your pallets.
1. `forklift config init`
1. `forklift config repos --add agrc/parcels` - The agrc/parcels is the user/repo to scan for Pallets.
1. `forklift garage open` - Opens garage directory. Copy all connection.sde files to the forklift garage.
1. `forklift git-update` - Updates pallet repos. Add any secrets or supplimentary data your pallets need that is not in source control.
1. Edit the `config.json` to add the arcgis server(s) to manage. The options property will be mixed in to all of the other servers.
    - `username` ArcGIS admin username.
    - `password` ArcGIS admin password.
    - `host` ArcGIS host address eg: `myserver`. Validate this property by looking at the `machineName` property returned by `/arcgis/admin/machines?f=json`
    - `port` ArcGIS server instance port eg: 6080
    ```json
    "servers": {
       "options": {
           "username": "mapserv",
           "password": "test",
           "port": 6080
       },
       "primary": {
           "host": "this.is.the.qualified.name.as.seen.in.arcgis.server.machines",
       },
       "secondary": {
           "host": "this.is.the.qualified.name.as.seen.in.arcgis.server.machines"
       },
       "backup": {
           "host": "this.is.the.qualified.name.as.seen.in.arcgis.server.machines",
           "username": "test",
           "password": "password",
           "port": 6443
       }
    }
    ```
1. Edit the `config.json` to add the email notification properties. _(This is required for sending email reports)_
    - `smtpServer` The SMTP server that you want to send emails with.
    - `smtpPort` The SMTP port number.
    - `fromAddress` The from email address for emails sent by forklift.
    ```json
    "email": {
        "smtpServer": "smpt.server.address",
        "smtpPort": 25,
        "fromAddress": "noreply@utah.gov"
    }
    ```
1. `forklift lift`
1. `forklift ship`

`run_forklift.bat` is an example of a batch file that could be used to run forklift via the Windows Scheduler.

## Development Usage

- create new env
  - `conda create --name forklift --clone arcgispro-py3`
  - `activate forklift`
- install deps
  - conda or pip install everything in the `setup.py` `install_requires`
- optionally install forklift
  - `cd forklift`
  - `pip install .\ -U`
- run forklift
  - for the installed version execute `forklift -h`
  - for the source version, from the `**/src**` directory, execute `python -m forklift -h` for usage

### Tests

#### On first run

- install deps
  - `pip install -e ".[tests]`
- run tests
  - `python setup.py develop`
  - `pytest`

_Tests that depend on a local SDE database (see `tests/data/UPDATE_TESTS.bak`) will automatically be skipped if it is not found on your system._

## Changelog

### 9.0.0

- Added `--send-emails` override option for both lift and ship commands.
- Added `ERROR` as a possible result type for crates.
- Removed unused crate property, `source_primary_key`
- BREAKING CHANGE: Split up lift and ship to be independant commands.
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
