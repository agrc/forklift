# Forklift AI Coding Agent Instructions

## Project Overview

**Forklift** is a Python CLI tool that automates geodatabase synchronization and data management tasks. It uses a "pallet" plugin architecture where users define data migration and processing jobs that execute in a strict lifecycle: `build` → `lift` (process) → `ship` (deploy).

Core use case: Schedule automated ArcGIS data updates with change detection, validation, service management, and reporting.

## Architecture

### Plugin System: Pallets and Crates

- **Pallet**: Base class ([models.py](src/forklift/models.py#L23)) users inherit to define jobs. Must have "pallet" in filename.
- **Crate**: Represents a single data transfer operation (source → destination with optional reprojection).
- Pallets are dynamically discovered and loaded from the `warehouse` folder via `importlib.util.spec_from_file_location()` ([engine.py#L845](src/forklift/engine.py#L845)).
- Single pallet file can contain multiple Pallet classes; target specific ones with `path/to/file.py:ClassName` syntax.

### Execution Pipeline

1. **Build**: Pallet.build(config) - pallets construct their crates and register copy locations
2. **Lift**: core.update() processes each crate: validates schema, checks for changes (via hash or change detection tables), and copies/reprojects data
3. **Ship**: Moves processed data from `dropoffLocation` to production `shipTo` location; optionally stops/restarts ArcGIS services
4. **Report**: Generates HTML reports; optionally sends via email/Slack

**Key files**: [engine.py](src/forklift/engine.py) (CLI commands), [core.py](src/forklift/core.py) (data update logic), [lift.py](src/forklift/lift.py) (pallet processing)

## Configuration & State Management

- Config stored in `forklift-garage/config.json` (created via `forklift config init`)
- State: Hash digests in `hashLocation`, staging data in `dropoffLocation`, production data in `shipTo`
- Change detection: Optional tables in `changeDetectionTables` override hash-based detection
- Pallet lifecycle properties: `success` (bool, message), `copy_data` (list of paths), `ship_on_fail`, `process_on_fail`

## Critical Patterns

### Error Handling

- Pallets catch exceptions in `build()`, set `self.success = (False, error_message)` — not raised
- Validation errors propagate via return tuples from [core.py](src/forklift/core.py) `update()` (returns status string, optional message)
- ArcGIS errors wrap `arcgisscripting.ExecuteError`; tests use mocks ([mocks.py](tests/mocks.py))

### Data Integrity

- Hash field `FORKLIFT_HASH` auto-added to track changes; stored in destination
- Metadata copied only on first crate creation; delete hash to force metadata refresh
- Global ID fields preserved in reprojection; special handling in [core.py#L120+](src/forklift/core.py#L120)

### Testing

- Pytest with fixtures from [conftest.py](tests/conftest.py): `test_gdb` manages geodatabase setup/teardown
- Mock ArcGIS via `pytest-mock` and custom mocks in [mocks.py](tests/mocks.py)
- Test data in `tests/data/` organized by module (e.g., `tests/data/test_pallet/`)
- Run tests: `pytest` (includes coverage, syntax check via ruff)

## Common Tasks

### Adding a New Command

1. Add docopt signature to [**main**.py](src/forklift/__main__.py#L7) usage string
2. Add handler function in [engine.py](src/forklift/engine.py)
3. Route in `main()` via docopt args

### Creating a Pallet

1. File must contain "pallet" (case-insensitive) in name; keep unique
2. Inherit from `Pallet` ([models.py](src/forklift/models.py#L23))
3. Implement `__init__()` with `super().__init__()` and `build(config)` to add crates
4. Optionally override: `validate_crate()`, `prepare_packaging()`, `post_copy_data()`
5. Example: [samples/PalletSamples.py](samples/PalletSamples.py#L1)

### Modifying Data Update Logic

- Entry point: `core.update(crate, validate_crate, change_detection)` ([core.py](src/forklift/core.py#L60))
- Reprojection: `_reproject()` adds `FORKLIFT_HASH` field; skipped if hash unchanged
- Change detection: Check `config.changeDetectionTables` before hashing ([core.py](src/forklift/core.py#L100+))

### Managing Dynamic Module Loading

- Pallet discovery: `_get_pallets_in_file()` ([engine.py#L859](src/forklift/engine.py#L859))
- Add folder to `sys.path` to enable imports; store module in `sys.modules` to cache
- Error handling: Failed imports logged, pallet skipped gracefully

## Dependencies & External Integration

- **ArcGIS**: arcpy, arcgis SDK 2.\* (requires Pro license; checked in [**main**.py](src/forklift/__main__.py#L73))
- **Data formats**: Handles FileGDB, ShapeFile, SDE connections
- **Reporting**: Email (SMTP or SendGrid), Slack webhooks, HTML templates in `src/forklift/templates/`
- **Git**: GitPython for repo cloning/updating; secure tokens via config
- **Logging**: Google Cloud Logging integration ([**main**.py](src/forklift/__main__.py#L85+))

## Dev Workflow

- **Setup**: Clone → `conda create --name forklift --clone arcgispro-py3` → `pip install -e .[tests]`
- **Test**: `pytest` (auto-runs coverage, syntax check, instafail reporter)
- **Build & Run**: Use batch files (`run_forklift_lift.bat`) or CLI directly
- **Debugging**: Set logging level with `--verbose` flag; check `forklift-garage/forklift.log.*`

## Key Implementation Details

- **xxhash** for fast data change detection (64-bit hash field)
- **Colorama** for cross-platform console colors
- **Pystache** for templating reports
- Pallet `.success` tuple determines lift continuation; `process_on_fail` forces processing regardless
- Service shutdown requires `folder/servicename` and type (e.g., `PoliticalDistricts`, `MapServer`)
