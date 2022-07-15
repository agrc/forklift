# 🚜📦✨ forklift

![conda](https://img.shields.io/badge/conda-arcgispro--py3-blue)
![python](https://img.shields.io/badge/python-3.6-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![GitHub tag (latest SemVer)](https://img.shields.io/github/v/tag/agrc/forklift?sort=semver)

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

- `changeDetectionTables` - An array of strings that are paths to change detection tables relative to the garage folder (e.g. `SGID.sde\\SGID.META.ChangeDetection`). A match between the source table name of a crate and a name from this table will cause forklift to skip hashing and use the values in the change detection table to determine if a crate's data needs to be updated. Each table should have the following fields:
  - `table_name` - A string field that contains a lower-cased, fully-qualified table name (e.g. `sgid.boundaries.counties`).
  - `hash` - A string that represents a unique hash of the entirety of the data in the table such that any change to data in the table will result in a new value.
- `configuration` - A configuration string (`Production`, `Staging`, or `Dev`) that is passed to `Pallet:build` to allow a pallet to use different settings based on how forklift is being run. Defaults to `Production`.
- `dropoffLocation` - The folder location where production ready files will be placed. This data will be compressed and will not contain any forklift artifacts. Pallets place their data in this location within their `copy_data` property.
- `email` - An object containing `fromAddress`, and `smptPort`, and `smtpServer` or a sendgrid `apiKey` for sending report emails.
- `hashLocation` - The folder location where forklift creates and manages data. This data contains hash digests that are used to check for changes. Referencing this location within a pallet is done by: `os.path.join(self.staging_rack, 'the.gdb')`.
- `notify` - An array of emails that will be sent the summary report each time `forklift lift` is run.
- `repositories` - A list of github repositories in the `<owner>/<name>` format that will be cloned/updated into the `warehouse` folder. A secure git repo can be added manually to the config in the format below:

  ```json
  "repositories": [{
    "host": "gitlabs.com/",
    "repo": "name/repo",
    "token": "personal access token with `read_repository` access only"
  }]
  ```

- `sendEmails` - A boolean value that determines whether or not to send forklift summary report emails after each lift.
- `servers` - An object describing one or more production servers that data will be shipped to. See below for more information.
- `serverStartWaitSeconds` - The number of seconds that forklift will wait after starting ArcGIS Server. Defaults to 300 (5 minutes).
- `shipTo` - A folder location that forklift will copy data to for each server. This is the datas' final location. Everything in the `dropoffLocation` will be copied to the `shipTo` location during a forklift ship. The `shipTo` path is optionally formatted with the `servers.host` value if present and necessary. Place a `{}` in your `shipTo` path if you would like to use this feature. eg: `\\\\{}\\c$\\data`.
- `warehouse` - The folder location where all of the `repositories` will be cloned into and where forklift will scan for pallets to lift.
- `slackWebhookUrl` - If you have a slack channel, you can login to the admin website and create a webhook url. If you set this property forklift will send reports to that channel.

Any of these properties can be set via the `config set` command like so:

```shell
forklift config set --key sendEmails --value False
```

If the property is a list then the value is appended to the existing list.

### Metadata

Metadata is only copied from source to destination when the destination is first created, not on subsequent data updates. If you want to push metadata updates, delete the destination in the hashing folder and then it will be updated when it is recreated on the next lift.

### Install to First Successful Run

From within the [ArcGIS Pro conda environment](http://pro.arcgis.com/en/pro-app/arcpy/get-started/using-conda-with-arcgis-pro.htm) (`c:\Program Files\ArcGIS\Pro\bin\Python\scripts\proenv.bat`):

1. Install [git](https://gitforwindows.org/).
1. Install [Visual Studio Build tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the Desktop development with C++ module
1. Install [ArcGIS Pro](https://pro.arcgis.com/en/pro-app/).
1. Add ArcGIS Pro to your path.
   - If installed for all users: `c:\Program Files\ArcGIS\Pro\bin\Python\scripts\`.
   - If install for single user: `C:\Users\{USER}\AppData\Local\Programs\ArcGIS\Pro\bin\Python\Scripts`.
1. Create a conda environment for forklift `conda create --name forklift python=3.9`.
1. Activate the conda environment `activate forklift`.
1. `conda install arcpy -c esri`
1. Chckout forklift repository: `git clone https://github.com/agrc/forklift.git` 
1. `pip install .\` from the directory containing `setup.py`.
1. Install the python dependencies for your pallets.
1. `forklift config init`
1. `forklift config repos --add agrc/parcels` - The agrc/parcels is the user/repo to scan for Pallets.
1. `forklift garage open` - Opens garage directory. Copy all connection.sde files to the forklift garage.
1. `forklift git-update` - Updates pallet repos. Add any secrets or supplementary data your pallets need that is not in source control.
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

### Upgrading Forklift

From the root of the forklift source code folder:

1. Activate forklift environment: `activate forklift`
1. Pull any new updates from GitHub: `git pull origin master`
1. Pip install with the upgrade option: `pip install .\ -U`

### Upgrading ArcGIS Pro

1. Upgrade ArcGIS Pro

There is no second step if you originally created a fresh conda environment (not cloned from `arcgispro-py3`) and installed arcpy via `conda install arcpy -c esri`.

If you do need to recreate the forklift environment from scratch, follow these steps:

1. Copy the `forklift-garage` folder to a temporary location.
1. Activate forklift environment: `activate forklift`
1. Export conda packages: `conda env export > env.yaml`
1. Export pip packages: `pip freeze > requirements.txt`
1. Remove and make note of any packages in `requirements.txt` that are not published to pypi such as forklift.
1. Deactivate forklift environment: `deactivate`
1. Remove forklift environment: `conda remove --name forklift --all`
1. Create new forklift environment: `conda create --clone arcgispro-py3 --name forklift --pinned`
1. Activate new environment: `activate forklift`
1. Reinstall conda packages: `conda env update -n forklift -f env.yaml`
1. Reinstall pip packages: `pip install -r requirements.txt`
1. Copy the `forklift-garage` folder to the site-packages folder of the newly created environment.
1. Reinstall forklift and any other missing pip package (from root of project): `pip install .\`

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
  - `pip install -e ".[tests]"`
- run tests
  - `python setup.py develop`
  - `pytest -p no:faulthandler`

`-p no:faulthandler` is to [prevent pytest from printing _tons_ of errors](https://stackoverflow.com/a/65826036/8049053).

_Tests that depend on a local SDE database (see `tests/data/UPDATE_TESTS.bak`) will automatically be skipped if it is not found on your system._

To run a specific test or suite: `pytest -k <test/suite name>`

If you have pip installed forklift into your current environment, you may need to uninstall it to get tests to see recent updates to the source code.
