🚜 Forklift
===================================
A CLI tool for managing a plethora of scheduled task python scripts.

> The first rule :tractor: is it does not work on any sabboth.   
> The second rule of :tractor: is your out of your element Donny.

### Usage
The work that forklift does is defined by plugins called [Pallets](src/forklift/models.py). `Pallet` is a base class that allows the user to define a job for forklift to perform by creating a new class that inherits from `Pallet`. Each pallet can have zero or more [Crates](src/forklift/models.py). A `Crate` is a class that defines data that needs to be moved from one location to another (reprojecting to web mercator by default). Crates are created by calling the `add_crates` (or `add_crate`) methods within `__init__` on the pallet. For example:
```python
class StringCratePallet(Pallet):
    def __init__(self):
        #: this call is required so that default properties are initialized
        super(StringCratePallet, self).__init__()

        destination_workspace = r'C:\\MapData'
        source_workspace = path.join(data_folder, 'agrc@sgid10.sde')

        self.add_crate('Counties', {'source_workspace': source_workspace,
                                    'destination_workspace': destination_workspace})
```
For details on all of the members of the `Pallet` and `Crate` classes see [models.py](src/forklift/models.py).

For examples of pallets see [samples/PalletSamples.py](samples/PalletSamples.py).

#### CLI
Interacting with forklift is done via the [command line interface](src/forklift/cli.py). Run `forklift -h` for a list of all of the available commands.

#### Config File Properties
`config.json` is created in the working directory after running `forklift config init`. It contains the following properties:
- `warehouse` The folder where all of the repositories will be cloned into and where forklift will scan for pallets to run.
- `sendEmails` Determines whether or not to send any emails. Set to `false` when testing.
- `notify` A list of emails that will be sent the summary report each time `forklift lift` is run (assuming `sendEmails: true`).
- `repositories` A list of repositories (`<owner>/<name>`) that will be cloned/updated into the warehouse folder.
- `copyDestinations` A list of folders that you want any data defined in `Pallet.copy_data` to be copied to upon successful processing of the pallet.

Any of these properties can be set via the `config set` command like so:
```
forklift config set --key sendEmails --value False
```
If the property is a list then the value is appended to the existing list.

### Install to First Successful Run
1. Update `secrets.py` based on the [sample.](/src/forklift/secrets_sample.py).
1. `pip install .\` from the directory containing `setup.py`.
2. `forklift config init`
4. `forklift config set --key copyDestinations --value c:\\MapData` - This is where you want your output placed.
3. `forklift repos --add agrc/parcels` - The agrc/parcesls is the user/repo to scan for Pallets.
4. `forklift lift`

### Development Usage
1. Update `secrets.py` based on the [sample.](/src/forklift/secrets_sample.py).
1. `pip install .\` from the directory containing `setup.py`.
1. from the `**/src**` directory execute `python -m forklift -h` for usage.

### Tests
`pip install tox`
`tox`

Tests that depend on a local SDE database (see `tests/data/UPDATE_TESTS.bak`) will automatically be skipped if it is not found on your system.
