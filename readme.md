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

1. `pip install .\` from the directory containing `setup.py`.
1. `forklift config init`
1. `forklift config set --key copyDestinations --value c:\\MapData` - This is where you want your output placed.
1. `forklift config set --key stagingDestinations --value c:\\staging` - This is where your data is staged for copy.
1. `forklift repos --add agrc/parcels` - The agrc/parcels is the user/repo to scan for Pallets.
1. `forklift garage open` - Add all connection.sde files to the forklift garage.
1. Set the following **user** environmental variables.
  - _required for sending email reports and/or starting/stopping ArcGIS Server Services_
  - _may require a reboot_
    - `FORKLIFT_SMTP_SERVER` The SMTP server that you want to send emails with.
    - `FORKLIFT_SMTP_PORT` The SMTP port number.
    - `FORKLIFT_FROM_ADDRESS` The from email address for emails sent by forklift.
    - `FORKLIFT_AGS_USERNAME` ArcGIS admin username.
    - `FORKLIFT_AGS_PASSWORD` ArcGIS admin password.
    - `FORKLIFT_AGS_SERVER_HOST` ArcGIS host address eg: `localhost`
1. Install [git](https://git-scm.com/)
1. `forklift lift`


#### Development Usage

1. `pip install .\` from the directory containing `setup.py`.
1. from the `**/src**` directory execute `python -m forklift -h` for usage.

#### Tests

On first run: `pip install tox`

On subsequent runs: `tox`


Tests that depend on a local SDE database (see `tests/data/UPDATE_TESTS.bak`) will automatically be skipped if it is not found on your system.
