# Project Architecture Blueprint — Forklift

> **Generated:** March 12, 2026  
> **Version analyzed:** 9.7.4 (setup.py) / 9.4.1 (`__main__.py` CLI version string)  
> **Technology:** Python 3, ArcGIS Pro (arcpy), ArcGIS API for Python  
> **Repository:** [agrc/forklift](https://github.com/agrc/forklift)

---

## Table of Contents

1. [Architectural Overview](#1-architectural-overview)
2. [Architecture Visualization](#2-architecture-visualization)
3. [Core Architectural Components](#3-core-architectural-components)
4. [Architectural Layers and Dependencies](#4-architectural-layers-and-dependencies)
5. [Data Architecture](#5-data-architecture)
6. [Cross-Cutting Concerns](#6-cross-cutting-concerns)
7. [Service Communication Patterns](#7-service-communication-patterns)
8. [Python-Specific Architectural Patterns](#8-python-specific-architectural-patterns)
9. [Implementation Patterns](#9-implementation-patterns)
10. [Testing Architecture](#10-testing-architecture)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Extension and Evolution Patterns](#12-extension-and-evolution-patterns)
13. [Architectural Pattern Examples](#13-architectural-pattern-examples)
14. [Architectural Decision Records](#14-architectural-decision-records)
15. [Architecture Governance](#15-architecture-governance)
16. [Blueprint for New Development](#16-blueprint-for-new-development)

---

## 1. Architectural Overview

Forklift is a **CLI-driven GIS data ETL pipeline orchestrator** built for ArcGIS Pro environments. Its core purpose is to automate the synchronization of geospatial datasets from upstream source databases to production ArcGIS Server instances, including change detection, data staging, and coordinated deployment.

### Guiding Principles

- **Plugin-First Design**: All data processing logic is delegated to user-defined `Pallet` subclasses. Forklift provides the engine; pallets provide the domain logic.
- **Two-Phase Pipeline Separation**: The `lift` phase (data extraction/preparation) is fully separated from the `ship` phase (production deployment). Each phase can run independently.
- **Hash-Based Change Detection**: Rather than timestamp or version tracking, forklift hashes every row's content (via xxhash) to determine true data changes, eliminating false positives from metadata-only edits.
- **Fail-Safe Data Delivery**: A packing slip (JSON manifest) bridges the two pipeline phases. Shipping without a prior lift is supported, guarding against orphaned deployments.
- **Idempotent Staging**: The drop-off location is purged and rebuilt on every lift, ensuring deterministic state before shipping.
- **Cloud-Aware Observability**: When running on Google Compute Engine, logs are automatically streamed to Google Cloud Logging in addition to local file/console output.

### Architectural Pattern

Forklift implements a **Plugin Pipeline Architecture**:

- A **Pipeline** defines a strict ordered sequence of operations (git update → build → detect changes → process → drop off → gift wrap → report).
- A **Plugin system** (Pallets) allows external callers to inject domain logic at defined lifecycle hook points without modifying the engine.

This pattern shares characteristics with the **Template Method Pattern** at the Pallet level, and a **Chain of Responsibility** at the pipeline operation level.

### Architectural Boundaries

| Boundary | Enforcement Mechanism |
|---|---|
| User plugin code vs. engine internals | `Pallet` abstract base class; only hooks are exposed |
| Lift phase vs. Ship phase | Packing slip JSON file at `dropoffLocation` |
| Source data vs. staging area | `hashLocation` file geodatabases (internal hash copies) |
| Staging area vs. production | `dropoffLocation` → `shipTo` copy via robocopy |
| ArcGIS Server control | `LightSwitch` abstraction over REST Admin API |
| Network share credentials | JSON files in `<garage>/share/<name>.json` |

---

## 2. Architecture Visualization

### High-Level System Context (C4 Level 1)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Forklift System                               │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────────┐    │
│  │  User /     │───▶│  CLI         │───▶│  Engine              │    │
│  │  Scheduler  │    │  (__main__)  │    │  (engine.py)         │    │
│  └─────────────┘    └──────────────┘    └──────┬───────────────┘    │
│                                                 │                    │
│         ┌───────────────────────────────────────┤                    │
│         │               │              │        │                    │
│         ▼               ▼              ▼        ▼                    │
│  ┌────────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐     │
│  │ Pallet     │  │  Core     │  │  Lift    │  │  Config      │     │
│  │ Plugins    │  │ (core.py) │  │ (lift.py)│  │ (config.py)  │     │
│  └────────────┘  └───────────┘  └──────────┘  └──────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
         │                │              │
         ▼                ▼              ▼
  ┌─────────────┐  ┌──────────┐  ┌──────────────────────┐
  │  Source SDE │  │ ArcGIS   │  │  ArcGIS Server       │
  │  Databases  │  │ Pro /    │  │  (REST Admin API)    │
  │  (*.sde)    │  │ arcpy    │  │                      │
  └─────────────┘  └──────────┘  └──────────────────────┘

  External:
  ┌────────────────────┐    ┌─────────────────────────┐
  │ Google Cloud       │    │ Network Shares           │
  │ Logging (if GCE)   │    │ (<garage>/share/*.json)  │
  └────────────────────┘    └─────────────────────────┘
```

### Lift Phase Pipeline (C4 Level 2 — Process)

```
forklift lift [file]
      │
      ▼
  git_update()          ← Pull all repos in config["repositories"]
      │
      ▼
  build_pallets()       ← Dynamic import via importlib.util; instantiate Pallets
      │
      ▼
  process_checklist()   ← Clear dropoffLocation; ensure hashLocation exists
      │
      ▼
  prepare_packaging()   ← Call pallet.prepare_packaging() on each pallet
      │
      ▼
  core.init()           ← Create/clear scratch.gdb
      │
      ▼
  process_crates()      ← For each unique crate: core.update() or change_detection.update()
      │                    (hash source rows; compare with destination; apply deltas)
      ▼
  process_pallets()     ← If crates changed: call pallet.process()
      │
      ▼
  dropoff_data()        ← Copy updated GDBs from hashLocation → dropoffLocation
      │
      ▼
  gift_wrap()           ← Strip FORKLIFT_HASH field; compact GDBs
      │
      ▼
  _generate_packing_slip()  ← Write packing-slip.json to dropoffLocation
      │
      ▼
  send reports (email / Slack)
```

### Ship Phase Pipeline (C4 Level 2 — Process)

```
forklift ship
      │
      ▼
  git_update()              ← Pull all repos (ensures pallet code is current)
      │
      ▼
  Read packing-slip.json from dropoffLocation
      │
      ▼
  For each ArcGIS Server in config["servers"]:
    │
    ├── LightSwitch.ensure("stop")    ← Stop server (or specific services)
    │
    ├── lift.copy_data()              ← robocopy dropoffLocation → shipTo
    │
    ├── LightSwitch.ensure("start")   ← Restart server
    │
    └── validate_service_state()      ← Confirm all services running
      │
      ▼
  For each pallet (from packing slip):
    ├── pallet.post_copy_process()
    └── pallet.ship()
      │
      ▼
  send reports (email / Slack)  ← Includes git_errors in ship report
```

### Component Dependency Graph

```
__main__.py
    └── engine.py
            ├── config.py
            ├── core.py
            │       ├── models.py (Crate, Changes)
            │       └── exceptions.py
            ├── lift.py
            │       ├── models.py (Pallet, Crate)
            │       ├── change_detection.py
            │       └── seat.py
            ├── models.py (Pallet, Crate, Changes)
            ├── arcgis.py (LightSwitch)
            ├── messaging.py
            ├── slack.py
            └── seat.py
                    └── config.py  (for garage path resolution)
```

---

## 3. Core Architectural Components

### 3.1 CLI Entry Point (`__main__.py`)

**Purpose**: Parse CLI arguments and dispatch to `engine` functions. Acts as the thin boundary between user input and engine logic.

**Key Responsibilities**:
- `docopt`-based argument parsing (the full CLI grammar is the module docstring)
- ArcGIS Pro license validation on import (fails fast with email notification if no license)
- Global unhandled exception handler (`_add_global_error_handler`)
- Logging configuration (`--verbose` flag enables DEBUG)
- `send_emails_override` flag routing (`--skip-emails` / `--send-emails`)
- **Google Cloud Logging integration** (new): If `is_running_on_gce()` returns `True`, a `google.cloud.logging.Client` is initialized and `setup_logging()` is called to stream all `forklift` logger output to Google Cloud Logging at DEBUG level.

**Log File Rotation**: Uses `RotatingFileHandler` with `backupCount=18` — rolls over the log file on every startup. This replaced the previous `TimedRotatingFileHandler` approach.

**GCE Detection** (`is_running_on_gce()`): Performs a 1-second HTTP GET to `http://metadata.google.internal/computeMetadata/v1/` with the `Metadata-Flavor: Google` header. Returns `True` only on GCE instances (and silently returns `False` on failures). Cloud Logging initialization failures are caught and logged as warnings — they do not abort startup.

**No business logic lives here.** All dispatch calls are pass-through to `engine`.

---

### 3.2 Engine (`engine.py`)

**Purpose**: Orchestrates all pipeline phases. The single largest module; coordinates all subsystems.

**Key Responsibilities**:
- `lift_pallets()`: Full lift pipeline execution
- `ship_data()`: Full ship pipeline execution (now also calls `git_update()` at the start; `git_errors` included in ship status report)
- `build_pallets()`: Dynamic pallet discovery and instantiation
- `load_module(module_name, module_path)`: **New** — loads a Python module from a file path using `importlib.util`; replaces the deprecated `imp.load_source`
- `git_update()` / `_clone_or_pull_repo()`: Repository management via GitPython
- `gift_wrap()`: Standalone data preparation command
- `scorched_earth()`: Reset staging state
- `speedtest()`: Performance benchmarking
- `init()` / `add_repo()` / `remove_repo()` / `list_repos()` / `list_pallets()`: Configuration management CLI commands
- `_generate_packing_slip()`: Write lift manifest to disk
- `_process_packing_slip()`: Read and hydrate pallets from manifest
- `_send_report_email()` / `_send_report_to_slack()`: Notification dispatch
- `_generate_console_report()`: Colorized terminal output via colorama

**Dynamic Module Loading** (updated): The `load_module()` function uses the modern `importlib.util` approach:
1. `importlib.util.spec_from_file_location(name, path)` — creates a module spec
2. `importlib.util.module_from_spec(spec)` — instantiates the module
3. `sys.modules[module_name] = module` — registers in the module cache
4. `spec.loader.exec_module(module)` — executes the module code

Guards against a `None` spec or loader (raised as `ImportError`), which was not possible with the old `imp.load_source`.

**Interaction Patterns**:
- Calls `config.get_config_prop()` extensively for runtime configuration
- Calls `lift.*` for all staging operations
- Calls `core.update` (passed as a function argument to `lift.process_crates_for`)
- Creates `LightSwitch` instances for ArcGIS Server control
- Creates `ChangeDetection` instance per lift run
- Uses `pystache` for HTML email template rendering

---

### 3.3 Models (`models.py`)

**Purpose**: Domain model layer. Defines the two core data entities — `Pallet` and `Crate` — and the `Changes` aggregate.

#### 3.3.1 `Pallet` (Plugin Base Class)

The plugin contract. Users subclass `Pallet` and override lifecycle hooks.

**Lifecycle Hooks** (in call order during lift):

| Method | When Called | Override Requirement |
|---|---|---|
| `__init__` | On instantiation | Optional (call `super().__init__()`) |
| `build(configuration)` | Before all processing; can raise safely | Recommended |
| `prepare_packaging()` | Before crate processing; only on explicit lift | Optional |
| `validate_crate(crate)` | Per crate, before update | Optional (custom validation) |
| `process()` | After crates updated; only if `requires_processing()` | Optional |
| `post_copy_process()` | After data copied to server; only if success | Optional |
| `ship()` | After server restart; on every ship | Optional |

**Control Properties**:

| Property | Type | Purpose |
|---|---|---|
| `ship_on_fail` | bool | Ship even if crates have errors |
| `process_on_fail` | bool | Process even if crates have errors |
| `copy_data` | list[str] | GDB paths to copy to `dropoffLocation` |
| `arcgis_services` | list[tuple] | Services to stop before `copy_data` copy |
| `destination_coordinate_system` | SpatialReference | Default output CRS (EPSG:3857) |
| `geographic_transformation` | str | Default datum transformation |

**State Properties** (managed by engine):

| Property | Type | Purpose |
|---|---|---|
| `success` | (bool, str\|None) | Overall pallet result |
| `_crates` | list[Crate] | Crate registry |
| `staging_rack` | str | Path to `hashLocation` |
| `garage` | str | Path to config directory |

#### 3.3.2 `Crate` (Data Transfer Unit)

Defines a single source → destination dataset pairing.

**Key State**:

| Property | Initialized | Purpose |
|---|---|---|
| `source` | ctor | Full path to source dataset |
| `source_workspace` | ctor | Source GDB/SDE path (lowercased) |
| `source_name` | ctor | Source table/feature class name |
| `destination` | ctor | Full path to destination dataset |
| `destination_workspace` | ctor | Destination GDB path (lowercased) |
| `destination_name` | ctor | Output table name |
| `result` | `UNINITIALIZED` → updated by core | Processing outcome tuple |
| `source_describe` | ctor (cached) | ArcGIS Describe metadata dict |
| `destination_coordinate_system` | ctor | Output CRS (from pallet default) |
| `name` | ctor | Unique hash-table identifier |

**Result Constants** (string constants on the class):

```
CREATED, UPDATED, INVALID_DATA, WARNING,
UPDATED_OR_CREATED_WITH_WARNINGS, NO_CHANGES,
UNHANDLED_EXCEPTION, UNINITIALIZED, ERROR
```

**Describe Cache**: Module-level `describes_cache` dict prevents repeated ArcGIS Describe calls for the same source across pallets.

#### 3.3.3 `Changes` (Delta Aggregate)

Holds the result of hashing a crate's source. Tracks which rows to add, delete, or leave unchanged, and holds a reference to the scratch feature class/table containing only the changed rows.

---

### 3.4 Core (`core.py`)

**Purpose**: Implements the hash-based change detection and physical data update logic. Pure data mechanics with no pipeline orchestration.

**Key Function**: `update(crate, validate_crate, change_detection)`

The update function follows this decision tree:

```
1. Destination doesn't exist?  → _create_destination_data() → CREATED
2. Custom validate_crate()?     → call it; or fall back to check_schema()
                                 → INVALID_DATA if validation fails
3. change_detection.has_table() → use external change detection
                                 → change_detection.update(crate)
4. else                         → _hash(crate) to compute Changes
                                 → if changes.has_changes():
                                     - has GlobalID? update_while_preserving_global_ids()
                                     - else: edit session → delete+insert deltas
                                   → UPDATED or CREATED
5. _check_counts(crate, changes) → sanity check row count match
```

**Hash Algorithm**: `xxhash.xxh64` over stringified row tuples. For feature classes, geometry is included as WKT. The hash is stored as a field (`FORKLIFT_HASH`, 16 chars) in the destination GDB.

**Scratch GDB**: A temporary `scratch.gdb` in the garage is created on each `core.init()` call and used for intermediate feature classes during the diffing process.

---

### 3.5 Lift (`lift.py`)

**Purpose**: Implements all file-system and GDB staging operations for the lift phase. Orchestrates pallet/crate iteration.

**Key Functions**:

| Function | Purpose |
|---|---|
| `process_checklist(config)` | Delete dropoffLocation; ensure hashLocation + changedetection.gdb exist |
| `prepare_packaging_for_pallets(pallets)` | Iterate pallets, call `prepare_packaging` with timing |
| `process_crates_for(pallets, update_def, change_detection)` | Deduplicated crate iteration; call `update_def` per unique destination |
| `process_pallets(pallets)` | Call `pallet.process()` on qualifying pallets |
| `dropoff_data(pallets, dropoff_location)` | Copy updated GDBs from hash location to dropoff |
| `gift_wrap(location)` | Strip `FORKLIFT_HASH` field from all GDBs; compact |
| `copy_data(from_location, to_template, ...)` | robocopy from dropoff to shipTo with rollback on failure |
| `get_lift_status(pallets, ...)` | Assemble status report dict |
| `copy_with_overwrite(source, destination)` | Recursive file copy (used for fallback copy) |

**Crate Deduplication**: `processed_crates` dict (keyed by `crate.destination`) ensures that if two pallets share the same destination dataset, `core.update` is called only once, and the result is shared.

---

### 3.6 Config (`config.py`)

**Purpose**: JSON config file reader/writer. Single source of truth for runtime parameters.

**Config File Location**: `<package_dir>/../forklift-garage/config.json`

**Config Properties**:

| Key | Type | Purpose |
|---|---|---|
| `changeDetectionTables` | list[str] | Paths (relative to garage) to `.sde` change detection tables |
| `configuration` | str | Environment tag: `"Production"`, `"Staging"`, or `"Dev"` |
| `dropoffLocation` | str | Directory for prepared data before shipping |
| `email` | dict | SMTP/SendGrid credentials |
| `hashLocation` | str | Directory for hash-augmented staging GDBs |
| `notify` | list[str] | Email addresses for reports |
| `repositories` | list[str] | GitHub repos (`owner/name`) containing pallets |
| `sendEmails` | bool | Whether to send email reports |
| `servers` | dict | ArcGIS Server connection profiles |
| `serverStartWaitSeconds` | int | Seconds to wait after server start/stop |
| `shipTo` | str | Template path for production data (supports `{machineName}`) |
| `warehouse` | str | Local directory where repos are cloned |

**Server Config Merging**: `get_config_prop("servers")` merges the `options` sub-dict (shared auth) into each named server entry, so individual server dicts override shared options.

---

### 3.7 Change Detection (`change_detection.py`)

**Purpose**: Alternative change detection strategy using externally managed change tables in SDE, instead of the internal hash approach.

**Data Model**: A persistent `changedetection.gdb/TableHashes` table in `hashLocation` stores previously seen hashes. On each run, current hashes from `changeDetectionTables` SDE paths are compared against stored hashes.

**When Used**: When `config["changeDetectionTables"]` is configured and the crate's `source_name` matches a table in those external tables. The `core.update` function defers to `change_detection.update(crate)` in this case.

**Update Strategy**: Truncate-and-append (not diff). Intentional for tables managed by external systems where row-level diffing is impractical.

---

### 3.8 ArcGIS Server Control (`arcgis.py`)

**Purpose**: `LightSwitch` class wraps the ArcGIS Server REST Admin API to stop/start the server or individual services.

**Retry Strategy**: 4 retries with exponential back-off `[12, 8, 4, 2, 1]` seconds.

**Token Management**: Lazily fetches and reuses auth tokens until `token_expire_milliseconds` is reached.

**Modes**:
- `ensure("stop"/"start")`: Stop/start the entire machine
- `ensure_services("off"/"on", services)`: Stop/start specific named services (for `--by-service` mode)
- `validate_service_state()`: Post-start verification that all configured services actually started

---

### 3.9 Messaging (`messaging.py`)

**Purpose**: Unified email notification. Supports both SMTP (legacy) and SendGrid (API key).

**Email Provider Selection**: If `email.apiKey` is non-empty in config, SendGrid is used; otherwise falls back to SMTP.

**Send Override**: `send_emails_override` module-level flag (set by CLI args) overrides the config `sendEmails` preference.

**Attachments**: Lift reports are sent with a gzipped JSON attachment (`packing-slip.json`).

---

### 3.10 Slack Integration (`slack.py`)

**Purpose**: Generates rich Slack Block Kit messages for lift and ship reports.

**Block Builders**: `Message`, `SectionBlock`, `ContextBlock`, `DividerBlock` classes compose Slack message payloads. `MAX_BLOCKS = 50` is enforced by splitting messages that exceed Slack's limit.

---

### 3.11 Seat (Utilities) (`seat.py`)

**Purpose**: Shared utility functions. Now includes infrastructure-level helpers alongside timing utilities.

**`format_time(seconds)`**: Human-friendly duration string (ms / seconds / minutes / hours).

**`timed_pallet_process`**: Context manager that wraps a named pallet lifecycle phase in `pallet.start_timer()` / `pallet.stop_timer()`. Used as `with seat.timed_pallet_process(pallet, "process"):`.

**`map_network_drive(name, drive_letter)`** (new): Maps a Windows network share as a drive letter using `net use`.
- Reads connection parameters (`path`, `username`, `password`) from `<garage>/share/<name>.json`
- Calls `subprocess.run(["net", "use", drive_letter, path, ...])` with `check=True`
- Tolerates error codes `85` and `1219` (drive already mapped) — logs at DEBUG and continues
- Other errors are re-raised as `Exception` with the stderr output
- Intended for use in pallet `build()` or `prepare_packaging()` to mount source data shares

> **Dependency note**: `seat.py` now imports `forklift.config` (for the garage path). This is a new dependency that was not present before. See §4 for implications.

---

## 4. Architectural Layers and Dependencies

```
┌─────────────────────────────────────────────┐
│  Presentation Layer                         │
│  __main__.py  (CLI, logging config)         │
└────────────────────┬────────────────────────┘
                     │ calls
┌────────────────────▼────────────────────────┐
│  Orchestration Layer                        │
│  engine.py   (pipeline coordination)        │
└──┬──────────────┬──────────┬────────────────┘
   │              │          │
   ▼              ▼          ▼
┌──────┐    ┌──────────┐  ┌──────────────────┐
│config│    │  lift.py │  │ arcgis.py        │
│.py   │    │(staging) │  │(server control)  │
└──────┘    └────┬─────┘  └──────────────────┘
                 │ calls
┌────────────────▼────────────────────────────┐
│  Domain / Processing Layer                  │
│  core.py  (hash + update)                   │
│  change_detection.py                        │
│  models.py  (Pallet, Crate, Changes)        │
└────────────────┬────────────────────────────┘
                 │ depends on
┌────────────────▼────────────────────────────┐
│  Infrastructure Layer                       │
│  arcpy  (ArcGIS Pro geoprocessing)          │
│  arcgis  (ArcGIS Python API v2)             │
│  xxhash  (content hashing)                  │
│  gitpython  (repo management)               │
│  google-cloud-logging  (cloud observability)│
│  requests  (HTTP / Slack / GCE metadata)    │
└─────────────────────────────────────────────┘

Cross-cutting:
  messaging.py, slack.py, seat.py, exceptions.py
  (used by engine, lift, models — minimal upward deps)
```

### Dependency Rules

- `__main__` → `engine` only (no direct access to lower layers)
- `engine` → `lift`, `config`, `core`, `arcgis`, `messaging`, `slack`, `models`, `seat`, `change_detection`
- `lift` → `core` (hash_field constant only), `models`, `change_detection`, `seat`
- `core` → `models`, `exceptions`, `config` (for garage path)
- `models` → `config`, `seat`, `messaging`, `arcpy`
- `change_detection` → `config`, `core` (one function), `models`
- `arcgis` → `requests` only (no internal modules)
- `messaging` → `config` only
- `slack` → `models` (Crate constants only)
- `seat` → `config` (for garage path, used by `map_network_drive`)
- `exceptions` → nothing

### No Circular Dependencies

The module graph is acyclic. `seat.py` now imports `config` — both are leaf-level modules with no back-edges, so this dependency does not create a cycle.

---

## 5. Data Architecture

### Geodatabase Locations

| Location | Config Key | Content | Lifecycle |
|---|---|---|---|
| Warehouse repos | `warehouse` | Source `.sde` connection files, pallet `.py` files | Persistent; managed by git |
| Hash staging | `hashLocation` | GDB copies of source data with `FORKLIFT_HASH` field | Persistent across runs; updated incrementally |
| Change detection | `hashLocation/changedetection.gdb` | `TableHashes` table: table name → hash | Persistent; updated per lift |
| Scratch | `garage/scratch.gdb` | Temporary diff tables/featureclasses | Cleared on every `core.init()` |
| Drop-off | `dropoffLocation` | Production-ready GDBs (no hash field) + `packing-slip.json` | Cleared on every lift; replaced |
| Production | `shipTo` | Final data location on ArcGIS Server | Updated during ship via robocopy |
| Share credentials | `garage/share/` | JSON files with network share credentials | Persistent; managed manually |

### Data Flow

```
Source SDE/GDB
    │
    │  core._hash()
    ▼
scratch.gdb/<crate.name>   (temp table with new/changed rows + FORKLIFT_HASH)
    │
    │  Edit session: delete old hash rows, insert new rows
    ▼
hashLocation/<pallet.copy_data GDB>   (staging GDB with FORKLIFT_HASH)
    │
    │  shutil.copytree (file copy, no lock files)
    ▼
dropoffLocation/<gdb_name>   (staging GDB, still has FORKLIFT_HASH)
    │
    │  lift.gift_wrap(): RemoveField FORKLIFT_HASH + Compact
    ▼
dropoffLocation/<gdb_name>   (clean GDB, production-ready)
    │
    │  robocopy /MIR
    ▼
shipTo/{machineName}/<gdb_name>   (PRODUCTION)
```

### Change Detection Model

**Hash-based (default)**: Each row in the destination GDB carries a `FORKLIFT_HASH` field (16-character xxh64 hex digest). On each lift, all source rows are hashed into a scratch table. The destination's existing hashes are loaded into a lookup dict. Rows present in scratch but not in destination hash lookup are added; rows in destination but absent from scratch are deleted.

**External Change Detection (optional)**: Configured via `changeDetectionTables`. An external SDE table provides pre-computed table-level hashes. If the hash has changed since the last lift, the destination is truncated and fully reloaded. This is a coarser-grained strategy suitable for tables where row-level diffing is impractical.

### Packing Slip Schema

The `packing-slip.json` bridges lift and ship phases:

```json
{
  "pallets": [
    {
      "name": "<file>:<class>",
      "success": true,
      "is_ready_to_ship": true,
      "requires_processing": true,
      "ship_on_fail": false,
      "message": "",
      "crates": [
        {
          "name": "<destination_name>",
          "result": "Data updated successfully.",
          "crate_message": "",
          "message_level": "",
          "source": "<full_source_path>",
          "destination": "<full_dest_path>",
          "was_updated": true
        }
      ],
      "total_processing_time": "1.23 seconds"
    }
  ]
}
```

### Network Share Credential Files

`seat.map_network_drive()` reads from `<garage>/share/<name>.json` with the following schema:

```json
{
  "path": "\\\\server\\share",
  "username": "DOMAIN\\user",
  "password": "secret"
}
```

These files must be created manually in the garage's `share/` subdirectory and are not managed by forklift commands. They contain credentials and must not be committed to version control.

---

## 6. Cross-Cutting Concerns

### 6.1 Logging

- **Logger Name**: All modules use `logging.getLogger("forklift")` — a single named logger shared across the entire system.
- **Log File**: Written to `<package_dir>/../forklift-garage/forklift.log` using `RotatingFileHandler` with `backupCount=18`. The log is rolled over on every startup (`file_handler.doRollover()`), keeping up to 18 previous log files.
- **Console Level**: INFO normally; DEBUG with `--verbose` flag.
- **Format**: `%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s`
- **Google Cloud Logging** (new): When `is_running_on_gce()` returns `True`, `google.cloud.logging.Client().setup_logging(log_level=DEBUG)` is called. This integrates the `forklift` logger with GCP's structured logging pipeline. GCL initialization failures are caught, logged as an error+warning, and execution continues — ensuring local logging is never blocked by cloud setup.
- **Pallet Standalone**: `Pallet.configure_standalone_logging()` allows a pallet to set up its own basicConfig for running outside the forklift process.
- **Performance Logging**: Every major pipeline phase is timed via `perf_counter()` and logged at INFO level.

### 6.2 Error Handling

**Strategy: Capture and Continue**

Forklift never raises unhandled exceptions that stop the pipeline. Instead:

- `build_pallets()` catches `ImportError` per file → `import_errors` list
- `lift.process_crates_for()` → `core.update()` wraps all ArcGIS operations in a `try/except` → `(UNHANDLED_EXCEPTION, str(e))`
- `lift.process_pallets()` wraps `pallet.process()` → sets `pallet.success = (False, str(e))`
- Ship phase wraps `pallet.post_copy_process()` and `pallet.ship()` individually
- Google Cloud Logging initialization is wrapped with `try/except` → logs warning, continues
- `map_network_drive()` catches error codes `85`/`1219` as non-fatal; all other subprocess errors re-raise
- All errors are captured in reports and communicated via email/Slack

**Custom Exception**: `ValidationException` (in `exceptions.py`) is the only domain exception, caught in `core.update` when `validate_crate` raises it.

**ArcGIS Workspace Cache**: `arcpy.ResetEnvironments()` and `arcpy.ClearWorkspaceCache_management()` are called after every crate update and at the start of `pallet.process()`.

### 6.3 Configuration Management

- Single JSON config file managed by `config.py`
- `config.config_location` is a module-level variable overridden by tests
- No environment variables used for runtime config
- Credentials (ArcGIS Server, email API keys, network share passwords) live in the garage — excluded from VCS
- Network share credentials stored separately in `<garage>/share/<name>.json`

### 6.4 Input Validation

- **Crate**: Destination name validated via `arcpy.ValidateTableName()` at `Crate.__init__` time
- **Pallet custom validation**: `validate_crate(crate)` hook with `ValidationException` — if not overridden, `core.check_schema()` verifies field type/length compatibility
- **Repo names**: `_validate_repo()` in `engine.py` calls GitHub API to verify `owner/repo` format
- **Server config**: `LightSwitch.__init__` checks for `None` credential fields and raises immediately
- **Module loading**: `load_module()` checks for `None` spec or loader (raises `ImportError`) before attempting execution

### 6.5 Resilience

- **Global ID preservation**: `update_while_preserving_global_ids()` for arcgis GlobalID values
- **Robocopy retry**: `copy_data()` uses robocopy with retry flags; error codes 8+ trigger rollback
- **Server stop/start retry**: `LightSwitch.ensure()` retries 4 times with exponential back-off
- **Pallet `ship_on_fail`**: Opt-in shipping even when crates failed
- **Network drive**: Drive-already-mapped errors are silently ignored (idempotent `map_network_drive`)
- **Cloud Logging**: GCL failure does not abort execution

### 6.6 Performance Instrumentation

- `seat.timed_pallet_process` wraps each pallet lifecycle phase
- `pallet.processing_times` dict accumulates named phase durations
- `forklift speedtest` runs a controlled benchmark for regression testing

---

## 7. Service Communication Patterns

### 7.1 ArcGIS Server REST Admin API

- **Protocol**: HTTP (configurable via config)
- **Auth**: Token-based (`/admin/generateToken`)
- **Endpoints Used**:
  - `POST /admin/machines/{machineName}/stop` / `start`
  - `POST /admin/services/{folder}/{name}.{type}/stop` / `start`
  - `GET /admin/services` (list all services)
  - `GET /admin/services/{path}/status`
- **Token Refresh**: Reused until `token_expire_milliseconds`; lazily refreshed

### 7.2 GitHub API

- Repo validation: `GET https://api.github.com/repos/{owner}/{repo}`
- Repo sync via GitPython (git protocol, not HTTP API)

### 7.3 Email

- **SMTP**: `smtplib.SMTP` with MIME multipart
- **SendGrid**: `sendgrid.SendGridAPIClient` with HTML body and optional gzipped attachment

### 7.4 Slack

- **Incoming Webhook**: HTTP POST with Block Kit JSON
- **Message Splitting**: >50-block messages split into multiple POSTs

### 7.5 Google Cloud Logging (new)

- **SDK**: `google-cloud-logging==3.*`
- **Auth**: Uses Application Default Credentials (ADC) — typically a GCE service account
- **Initialization**: Conditional — only when `is_running_on_gce()` returns `True`
- **Integration**: `client.setup_logging()` attaches a GCP handler to the root logger at DEBUG level
- **Fallback**: On any initialization exception, local logging continues unaffected

### 7.6 Network Shares (new)

- **Protocol**: Windows `net use` command via `subprocess`
- **Credential source**: `<garage>/share/<name>.json`
- **Persistence**: `/persistent:yes` flag maintains the mapping across reboots
- **Idempotency**: Re-mapping an already-mapped drive is silently ignored (error 85/1219)

### 7.7 GCE Metadata Server

- **URL**: `http://metadata.google.internal/computeMetadata/v1/`
- **Header**: `Metadata-Flavor: Google`
- **Timeout**: 1 second — fail-fast on non-GCE environments
- **Purpose**: Environment detection for conditional Cloud Logging initialization

### 7.8 No Internal Service Communication

Forklift is a single-process monolith. All coordination is through shared file system paths (staging directories, packing slip, share credential files).

---

## 8. Python-Specific Architectural Patterns

### 8.1 Module Organization

```
src/forklift/
├── __init__.py          (empty — namespace package)
├── __main__.py          (CLI entry; entry_points["console_scripts"])
├── engine.py            (pipeline orchestration)
├── models.py            (domain classes)
├── core.py              (hash-based ETL mechanics)
├── lift.py              (staging operations)
├── config.py            (config file I/O)
├── change_detection.py  (external change detection)
├── arcgis.py            (ArcGIS Server REST client)
├── messaging.py         (email notifications)
├── slack.py             (Slack Block Kit builder)
├── seat.py              (utility functions + network drive mapping)
├── exceptions.py        (custom exception types)
└── templates/
    ├── lift.html        (Mustache template for lift email)
    └── ship.html        (Mustache template for ship email)
```

### 8.2 Dynamic Module Loading (updated)

`engine.build_pallets()` uses the new `load_module()` function which leverages `importlib.util`:

```python
def load_module(module_name, module_path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from path {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
```

This replaces the deprecated `imp.load_source()` (Python 3.12+ incompatible). The `pallet_file_regex = re.compile(r"pallet.*\.py$")` regex still filters candidate files.

### 8.3 Dependency Management

- **Package distribution**: `setup.py` with `find_packages("src")` and `package_dir={"": "src"}`
- **Runtime dependencies** (current): `arcgis==2.*`, `colorama==0.*`, `docopt==0.6.*`, `gitpython==3.*`, `google-cloud-logging==3.*`, `ndg-httpsclient==0.*`, `pyasn1==0.*`, `pyopenssl>=24,<26`, `pystache==0.*`, `requests==2.*`, `sendgrid==6.*`, `xxhash==3.*`
- **arcpy**: Not in `install_requires` — provided by ArcGIS Pro conda environment
- **Test extras**: `pytest>=8`, `pytest-cov>=5,<8`, `pytest-mock==3.*`, `pytest-ruff==0.*`, `pytest-instafail==0.5.*`, `ruff==0.*`

### 8.4 OOP vs. Functional Style

- **Plugin interface** (`Pallet`, `Crate`, `LightSwitch`, `ChangeDetection`, Slack block classes): Class-based
- **Pipeline operations** (`engine`, `lift`, `core`): Module-level functions (functional style)
- **Utilities** (`seat`): Mix — `format_time` is a module-level function; `timed_pallet_process` is a context manager class; `map_network_drive` is a module-level function

### 8.5 Context Managers

`seat.timed_pallet_process` implements `__enter__` / `__exit__` for timing. Used in `with` blocks throughout `lift.py` and `engine.py`.

### 8.6 Module-Level State

Several modules use module-level mutable state:
- `models.names_cache`, `models.describes_cache`: Performance caches for ArcGIS metadata
- `messaging.send_emails_override`: Runtime flag set by CLI args
- `core.log`: Logger reference, set by `core.init(logger)` to allow external injection
- `config.config_location`: Overridden in tests to redirect config I/O

---

## 9. Implementation Patterns

### 9.1 Pallet Lifecycle Implementation Template

```python
from forklift.models import Pallet
from forklift import seat
from os import path

class MyPallet(Pallet):
    def __init__(self):
        super().__init__()
        self.my_gdb = path.join(self.staging_rack, "my_data.gdb")
        self.copy_data = [self.my_gdb]
        self.arcgis_services = [("MyFolder/MyService", "MapServer")]
        self.destination_coordinate_system = 26912  # UTM NAD83 Zone 12N

    def build(self, configuration="Production"):
        # Optional: mount a network share before accessing source data
        seat.map_network_drive("my_share", "Z:")
        source_sde = path.join(self.garage, "my_source.sde")
        self.add_crates(
            ["TableA", "TableB"],
            {"source_workspace": source_sde, "destination_workspace": self.my_gdb}
        )

    def validate_crate(self, crate):
        from forklift.exceptions import ValidationException
        if crate.source_name == "TableA":
            if not some_condition:
                raise ValidationException("Custom validation failed")
        return NotImplemented

    def process(self):
        self.log.info("Running post-update processing")

    def post_copy_process(self):
        pass

    def ship(self):
        pass
```

### 9.2 Crate Construction Patterns

```python
# Pattern 1: String shorthand (use defaults for both workspaces)
self.add_crates(["TableA", "TableB"], defaults={
    "source_workspace": source_sde,
    "destination_workspace": self.my_gdb
})

# Pattern 2: 2-tuple (source_name, source_workspace); destination_workspace from defaults
self.add_crates(
    [("TableA", alt_sde)],
    defaults={"destination_workspace": self.my_gdb}
)

# Pattern 3: 3-tuple (source_name, source_workspace, destination_workspace)
self.add_crates([("TableA", source_sde, dest_gdb)])

# Pattern 4: 4-tuple (source_name, source_workspace, destination_workspace, destination_name)
self.add_crates([("source_table", source_sde, dest_gdb, "renamed_table")])

# Pattern 5: Single crate via add_crate
self.add_crate(("TableA", source_sde, dest_gdb))
```

### 9.3 Network Drive Mapping Pattern (new)

```python
# In <garage>/share/my_share.json:
# { "path": "\\\\server\\sharename", "username": "DOMAIN\\user", "password": "secret" }

# In pallet build():
from forklift import seat

def build(self, configuration="Production"):
    seat.map_network_drive("my_share", "Z:")   # idempotent; ignores "already mapped"
    source_sde = "Z:\\data\\my_source.sde"
    self.add_crates(["MyTable"], {"source_workspace": source_sde, "destination_workspace": self.my_gdb})
```

### 9.4 Custom Validation Pattern

```python
from forklift.exceptions import ValidationException

def validate_crate(self, crate):
    if crate.source_name.lower() == "mytable":
        import arcpy
        count = int(arcpy.GetCount_management(crate.source)[0])
        if count < 100:
            raise ValidationException(f"Expected ≥100 rows, got {count}")
        return True  # explicitly valid; skip schema check
    return NotImplemented  # defer to default schema check
```

### 9.5 Error Handling Within Pallet Hooks

```python
def process(self):
    try:
        # ... processing logic ...
        pass
    except Exception as e:
        self.success = (False, str(e))
        # Forklift reads self.success for reporting; do not re-raise
```

### 9.6 Report Data Contract

**Pallet report keys**: `name`, `success`, `is_ready_to_ship`, `requires_processing`, `ship_on_fail`, `message`, `crates[]`, `total_processing_time`

**Crate report keys**: `name`, `result`, `crate_message`, `message_level`, `source`, `destination`, `was_updated`

**Ship status report keys** (updated): `hostname`, `total_pallets`, `pallets`, `num_success_pallets`, `server_reports`, `total_time`, `git_errors` (new — git errors are now surfaced in ship reports)

---

## 10. Testing Architecture

### 10.1 Test Strategy

- **Framework**: pytest with `pytest-cov`, `pytest-mock`, `pytest-ruff`, `pytest-instafail`
- **Coverage**: Branch coverage enabled (`--cov-branch`); XML report generated (`cov.xml`)
- **Lint**: `pytest-ruff` runs ruff as part of the test suite

### 10.2 Test Organization

```
tests/
├── conftest.py              Session-scoped config isolation fixture
├── mocks.py                 Shared mock pallet/crate factories
├── test_arcgis.py           LightSwitch unit tests (heavy mocking of requests)
├── test_change_detection.py ChangeDetection unit tests
├── test_changes.py          Changes model tests (core hashing behavior)
├── test_config.py           Config read/write tests
├── test_core.py             core.update path tests (requires real arcpy)
├── test_crate.py            Crate model tests
├── test_engine.py           Engine function tests
├── test_lift.py             Lift staging operation tests
├── test_messaging.py        Email/SMTP tests
├── test_pallet.py           Pallet lifecycle tests
├── test_seat.py             Utility tests
├── test_slack.py            Slack block builder tests
├── benchmark_arcgis.py      Performance benchmarks (not run in CI)
├── data/                    Test GDBs (as .zip), pallet files, config fixtures
└── maps/                    ArcMap MXDs for schema lock tests
```

### 10.3 Key Test Fixtures

**`conftest.setup` (session-scoped)**: Redirects `config.config_location` to `tests/config.json`, creates a default config before the session, deletes after.

**`conftest.test_gdb` (function-scoped)**: Looks for `tests/data/<module>/<test_name>.gdb` or `.zip`. Copies to `tmp_path` for isolated mutation. Auto-zips unzipped GDBs after a successful test run.

### 10.4 Mocking Approach

- `pytest-mock` (`mocker.patch`) for module-level function mocking
- `unittest.mock.Mock` / `mock_open` for object mocking
- ArcGIS-heavy tests use real `arcpy` with test GDBs
- ArcGIS Server tests mock `requests` entirely
- `is_running_on_gce()` should be mocked in `__main__` tests to control Cloud Logging initialization

### 10.5 Test Data Strategy

Test GDBs stored as `.zip` files in `tests/data/`. The `test_gdb` fixture extracts them to `tmp_path` before each test and zips them back if the test passes. This keeps git history clean and ensures deterministic test state.

---

## 11. Deployment Architecture

### 11.1 Installation

```
conda activate arcgispro-py3
pip install forklift
forklift config init
```

### 11.2 Directory Structure (Production)

```
c:\forklift\
├── warehouse\              ← cloned GitHub repos (pallets)
│   ├── my-project\
│   │   └── my_pallet.py
│   └── ...
└── data\
    ├── hashed\             ← hashLocation: staging GDBs with FORKLIFT_HASH
    │   ├── changedetection.gdb
    │   └── my_data.gdb
    └── receiving\          ← dropoffLocation: between lift and ship
        ├── packing-slip.json
        └── my_data.gdb

src\forklift\forklift-garage\
├── config.json             ← runtime config
├── forklift.log            ← rotating log (backupCount=18)
├── forklift.log.1 ... .18  ← log rotation history
├── scratch.gdb             ← created/cleared per lift
├── share\                  ← NEW: network share credential files
│   └── my_share.json
└── *.sde                   ← SDE connection files used by pallets
```

### 11.3 ArcGIS Server Production Path

```
c:\arcgisserver\directories\arcgisinput\   (or config.shipTo)
├── primary\
│   └── my_data.gdb         ← production data
```

The `shipTo` config value supports `{machineName}` placeholder for multi-server deployments.

### 11.4 Scheduled Execution

- **Lift**: `run_forklift_lift.bat` → `forklift lift`
- **Ship**: `run_forklift_ship.bat` → `forklift ship`
- **Lift+Ship**: `run_forklift_ship_lift.bat`

### 11.5 Google Cloud Deployment

When forklift runs on a GCE VM:
1. `is_running_on_gce()` queries the GCE metadata server and returns `True`
2. `google.cloud.logging.Client()` uses the VM's service account ADC (no explicit credentials needed)
3. `client.setup_logging(log_level=DEBUG)` attaches a GCP handler — all `forklift` logger output flows to Cloud Logging
4. Local log file and console output continue in parallel

The VM service account requires the `roles/logging.logWriter` IAM role.

### 11.6 Environment-Specific Behavior

The `configuration` config property (`Production`, `Staging`, `Dev`) is passed to `pallet.build(configuration)`. Pallets can branch on this to use different source databases. Forklift itself does not alter behavior based on this value.

### 11.7 Warehouse Management

GitHub repositories are cloned to `config["warehouse"]`. `forklift git-update` pulls all configured repos. The `pallet_file_regex` discovers all `*pallet*.py` files (case-insensitive) recursively within the warehouse.

---

## 12. Extension and Evolution Patterns

### 12.1 Adding a New Pallet

1. Create `<project_name>_pallet.py` with `pallet` in the filename
2. Subclass `Pallet` from `forklift.models`
3. Implement `build()`: define crates, set `copy_data`, optionally call `seat.map_network_drive()`
4. Optionally implement `process()`, `ship()`, `post_copy_process()`
5. Add repo: `forklift config repos --add owner/repo`

### 12.2 Adding a Network Share Credential

1. Create `<garage>/share/<name>.json` with `path`, `username`, `password` keys
2. Call `seat.map_network_drive("<name>", "<drive_letter>:")` in pallet `build()`

### 12.3 Adding a New Change Detection Strategy

1. Create a class with `has_table(name) → bool` and `update(crate) → (str, str|None)`
2. Instantiate in `engine.lift_pallets()` and pass to `lift.process_crates_for()`

### 12.4 Adding a New Notification Channel

1. Create a module alongside `messaging.py` and `slack.py`
2. Implement a `send_*(report)` function
3. Call it in `engine._send_report_*` helpers
4. Add any required config keys to `config.create_default_config()`

### 12.5 Integrating a New ArcGIS Server Version

1. Subclass `LightSwitch` in `arcgis.py`
2. Override URL construction or endpoint methods
3. Instantiate the new class in `engine.ship_data()`

### 12.6 Disabling Google Cloud Logging

`is_running_on_gce()` controls the GCL integration automatically. To force it off even on GCE, mock or override `is_running_on_gce` to return `False`. No config knob currently exists for this.

### 12.7 Deprecation Patterns

- `imp.load_source` migration to `importlib.util` is **complete** as of this version (ADR-006 resolved)
- No other deprecated APIs currently in use

---

## 13. Architectural Pattern Examples

### 13.1 Template Method Pattern — Pallet Lifecycle

```python
# Base class (models.py) — defines hook methods
class Pallet(object):
    def build(self, configuration="Production"):
        return  # Subclass override

    def process(self):
        return NotImplemented  # Subclass override

    def ship(self):
        return NotImplemented  # Subclass override

# Engine (engine.py) — calls hooks in defined order
for pallet in pallets:
    pallet.build(config.get_config_prop("configuration"))
    # ... later:
    pallet.process()
    # ... later:
    pallet.ship()
```

### 13.2 Plugin Discovery — importlib-based Module Loading (updated)

```python
# engine.py
pallet_file_regex = compile(r"pallet.*\.py$")

def load_module(module_name, module_path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from path {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
```

### 13.3 Strategy Pattern — Update Function Injection

```python
# lift.py — update_def is injected, not imported
def process_crates_for(pallets, update_def, change_detection=None):
    for pallet in pallets:
        for crate in pallet.get_crates():
            crate.set_result(update_def(crate, pallet.validate_crate, change_detection))

# engine.py — production
lift.process_crates_for(pallets_to_lift, core.update, change_detection)

# test — mock injection
mock_update = Mock(return_value=(Crate.NO_CHANGES, None))
lift.process_crates_for(pallets, mock_update, mock_change_detection)
```

### 13.4 Packing Slip — Decoupled Phase Communication

```python
# Lift phase writes
def _generate_packing_slip(status, dropoff_location):
    packing_slip_path = join(dropoff_location, packing_slip_file)
    with open(packing_slip_path, "w", encoding="utf-8") as f:
        dump(status, f, indent=2)

# Ship phase reads and hydrates
def _process_packing_slip(packing_slip=None, pallet_arg=None):
    location = join(config.get_config_prop("dropoffLocation"), packing_slip_file)
    with open(location, "r", encoding="utf-8") as slip:
        packing_slip = load(slip)
    # ... hydrate pallets from slip entries ...
```

### 13.5 Context Manager — Timed Process

```python
# seat.py
class timed_pallet_process(object):
    def __enter__(self):
        self.pallet.start_timer(self.name)
    def __exit__(self, type, value, traceback):
        self.pallet.stop_timer(self.name)

# Usage (lift.py)
with seat.timed_pallet_process(pallet, "process"):
    pallet.process()
```

### 13.6 Conditional Cloud Logging — GCE Detection

```python
# __main__.py
def is_running_on_gce():
    try:
        response = requests.get(
            'http://metadata.google.internal/computeMetadata/v1/',
            headers={'Metadata-Flavor': 'Google'},
            timeout=1
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def _setup_logging(verbose):
    # ... configure local handlers ...
    if is_running_on_gce():
        try:
            client = google.cloud.logging.Client()
            client.setup_logging(log_level=logging.DEBUG)
        except Exception as e:
            log.error("Failed to initialize Google Cloud Logging: %s", e)
            log.warning("Continuing without Google Cloud Logging.")
```

### 13.7 Crate Deduplication — Shared Destination Protection

```python
# lift.py
def process_crates_for(pallets, update_def, change_detection=None):
    processed_crates = {}
    for pallet in pallets:
        for crate in pallet.get_crates():
            if crate.destination not in processed_crates:
                processed_crates[crate.destination] = crate.set_result(
                    update_def(crate, pallet.validate_crate, change_detection)
                )
            else:
                crate.set_result(processed_crates[crate.destination])
```

---

## 14. Architectural Decision Records

### ADR-001: Plugin Architecture for Data Processing Logic

**Context**: Forklift must support diverse GIS data workflows across many projects and source systems.

**Decision**: Plugin system where all data-specific logic lives in external `Pallet` subclasses, discovered via filename convention (`*pallet*.py`) and dynamically loaded.

**Consequences**:
- (+) Engine is stable; adding new workflows requires no engine changes
- (+) Pallets versioned and deployed independently via git repos
- (+) Easy to test pallets in isolation
- (-) No formal plugin API versioning; breaking changes in `Pallet` affect all pallets

---

### ADR-002: Two-Phase Lift/Ship Pipeline Separation

**Context**: Data preparation (long-running) should not hold the ArcGIS server down during deployment.

**Decision**: Separate `lift` and `ship` into independent CLI commands, bridged by a JSON packing slip file.

**Consequences**:
- (+) Lift can run on any schedule without affecting server uptime
- (+) Ship can be triggered on a maintenance window schedule
- (-) Requires filesystem coordination between two process invocations

---

### ADR-003: Hash-Based Row-Level Change Detection

**Context**: ArcGIS geodatabases have inconsistent support for version-based change tracking.

**Decision**: `xxhash.xxh64` content hash per row, stored in `FORKLIFT_HASH` field, stripped before delivery via `gift_wrap`.

**Consequences**:
- (+) Works with any ArcGIS data source
- (+) True change detection (not timestamp-based)
- (-) Hashing all rows is CPU-intensive (hence `speedtest` command)
- (-) Duplicate rows handled by hash-appending, affecting row identity semantics

---

### ADR-004: JSON Config File for Runtime Configuration

**Context**: Need configurable deployment targets, email servers, warehouse locations.

**Decision**: Single `config.json` in `forklift-garage`. Managed via `forklift config` sub-commands.

**Consequences**:
- (+) Simple; no external dependency
- (-) Credentials stored in plaintext JSON; no secrets management integration
- (-) Supplemented by `share/<name>.json` pattern for network share credentials (same tradeoff)

---

### ADR-005: robocopy for Production Data Delivery

**Context**: GDB delivery on Windows requires handling file locks and atomic delivery.

**Decision**: `robocopy /MIR` with `/fft`, `/xf *.lock`, `/z`; exit codes 8+ trigger rollback.

**Consequences**:
- (+) Battle-tested tool with built-in retry
- (-) Windows-only (acceptable since arcpy is also Windows-only in this context)

---

### ADR-006: Migrate `imp.load_source` → `importlib.util` ✅ RESOLVED

**Context**: `imp` module deprecated since Python 3.4; removed in Python 3.12.

**Decision**: Replaced with `load_module()` using `importlib.util.spec_from_file_location` + `module_from_spec` + `exec_module`. Module is registered in `sys.modules` for proper import semantics. Added guard for `None` spec/loader (raises `ImportError` with descriptive message).

**Status**: **Implemented** in v9.7.4. Python 3.12+ compatibility restored.

---

### ADR-007: Google Cloud Logging Integration (new)

**Context**: Forklift is being deployed on GCE VMs where structured log aggregation via Google Cloud Logging is preferred over log file shipping.

**Decision**: Auto-detect GCE by querying the GCE metadata server with a 1-second timeout. If detected, initialize `google.cloud.logging.Client` and call `setup_logging()`. Failures during initialization are non-fatal — local logging continues.

**Consequences**:
- (+) Zero-configuration on GCE — uses service account ADC
- (+) On-premises deployments are completely unaffected (metadata endpoint unreachable → `False` in <1s)
- (+) Fallback is graceful — a warning is logged and execution continues
- (-) Adds `google-cloud-logging==3.*` as a mandatory install-time dependency even for non-GCE deployments
- (-) No config flag to explicitly disable GCL on GCE (requires code-level override)

---

### ADR-008: Network Share Credential Files (new)

**Context**: Some source data is on Windows network shares that must be mounted before pallet `build()` can reference them. Credentials must be stored outside of version control.

**Decision**: `seat.map_network_drive(name, drive_letter)` reads `<garage>/share/<name>.json` containing `path`, `username`, `password`. Uses `net use /persistent:yes`. Already-mapped errors (85, 1219) are silently ignored.

**Consequences**:
- (+) Decouples credential management from pallet code
- (+) Idempotent — safe to call on every pallet build
- (+) Consistent credential storage location (alongside other garage secrets)
- (-) Plain-text credentials in JSON; no encryption at rest
- (-) Windows-only (`net use`)
- (-) `seat` module now has a `config` dependency (was previously a pure utility)

---

## 15. Architecture Governance

### 15.1 Consistency Mechanisms

- **Pallet contract**: `Pallet` base class in `models.py` is the single source of truth for the plugin API
- **Crate result constants**: String constants on the `Crate` class define all valid states
- **Config schema**: `config.create_default_config()` is the canonical schema definition
- **Module loading**: `load_module()` in `engine.py` is the single, authoritative entry point for dynamic Python file loading

### 15.2 Automated Checks

- **Linting**: `ruff` (configured in `pyproject.toml`); run as part of `pytest` via `pytest-ruff`
- **Test coverage**: `pytest-cov` with branch coverage
- **Import validation**: `build_pallets()` captures pallet import errors as `import_errors`

### 15.3 Documentation Practices

- All public functions have module-level docstrings with parameter types
- `Pallet` and `Crate` are extensively documented inline (external-facing API)
- CLI grammar in `__main__.py`'s module docstring serves as primary user-facing documentation
- `samples/` directory contains canonical pallet implementation examples
- `<garage>/share/` credential files are not documented by forklift — operators must manage them manually

### 15.4 Versioning

Semantic versioning. `setup.py` carries `9.7.4`; CLI docopt string carries `9.4.1` (these should be kept synchronized — currently diverged). `CHANGELOG.md` tracks version history.

---

## 16. Blueprint for New Development

### 16.1 Development Workflow

#### Adding a New Pallet

1. Create `<project_name>_pallet.py` in your project's GitHub repo
2. Import `from forklift.models import Pallet`
3. Implement `build(configuration)` — define all crates and `copy_data`
4. If source data is on a network share, call `seat.map_network_drive()` at the top of `build()`
5. Test locally: `forklift lift path/to/my_project_pallet.py --verbose`
6. Add repo to config: `forklift config repos --add owner/repo`

#### Adding a Network Drive

1. Create `<garage>/share/<name>.json` with credentials
2. Call `seat.map_network_drive("<name>", "<drive>:")` in pallet `build()`
3. Reference the drive letter in source workspace paths

#### Adding an Engine Feature

1. Identify the appropriate module (`engine.py`, `core.py`, or `lift.py`)
2. Add unit tests in the corresponding `tests/test_*.py` file
3. If a new config property is needed, add it to `config.create_default_config()`
4. Update `__main__.py` docstring if a new CLI command is added
5. Update `CHANGELOG.md`

### 16.2 Implementation Templates

#### Minimal Pallet

```python
from os import path
from forklift.models import Pallet

class MinimalPallet(Pallet):
    def build(self, configuration="Production"):
        source_sde = path.join(self.garage, "my_source.sde")
        dest_gdb = path.join(self.staging_rack, "my_data.gdb")
        self.copy_data = [dest_gdb]
        self.add_crates(["MyTable"], {
            "source_workspace": source_sde,
            "destination_workspace": dest_gdb
        })
```

#### Pallet with Network Share

```python
from os import path
from forklift.models import Pallet
from forklift import seat

class NetworkSharePallet(Pallet):
    def __init__(self):
        super().__init__()
        self.my_gdb = path.join(self.staging_rack, "project.gdb")
        self.copy_data = [self.my_gdb]

    def build(self, configuration="Production"):
        seat.map_network_drive("my_share", "Z:")   # reads garage/share/my_share.json
        self.add_crates(["TableA"], {
            "source_workspace": "Z:\\data\\source.sde",
            "destination_workspace": self.my_gdb
        })
```

#### Pallet with Full Lifecycle

```python
from os import path
from forklift.models import Pallet
from forklift.exceptions import ValidationException

class FullLifecyclePallet(Pallet):
    ship_on_fail = False

    def __init__(self):
        super().__init__()
        self.my_gdb = path.join(self.staging_rack, "project.gdb")
        self.copy_data = [self.my_gdb]
        self.arcgis_services = [("MyFolder/MyService", "MapServer")]

    def build(self, configuration="Production"):
        sde = path.join(self.garage, "source.sde")
        self.add_crates(["FeatureClassA", "TableB"], {
            "source_workspace": sde, "destination_workspace": self.my_gdb
        })

    def validate_crate(self, crate):
        if crate.source_name == "FeatureClassA":
            import arcpy
            count = int(arcpy.GetCount_management(crate.source)[0])
            if count == 0:
                raise ValidationException("FeatureClassA must not be empty")
            return True
        return NotImplemented

    def process(self):
        self.log.info("Running post-update ETL transforms")

    def post_copy_process(self):
        pass

    def ship(self):
        self.log.info("Notifying downstream systems")
```

### 16.3 Common Pitfalls

| Pitfall | Correct Pattern |
|---|---|
| Importing `core`, `lift`, or `engine` from a pallet | Only import from `forklift.models`, `forklift.exceptions`, `forklift.config`, `forklift.seat` |
| Raising exceptions from `__init__` | Move risky logic to `build()` |
| Forgetting to call `super().__init__()` | Always call in pallet `__init__` |
| Hardcoded file paths in pallets | Use `self.garage`, `self.staging_rack`, or mounted drive letters |
| Manually editing `FORKLIFT_HASH` field | Never interact with hash fields; `gift_wrap` handles removal |
| Assuming `ship()` is only called when data changed | `ship()` is called on every ship; use `requires_processing()` to gate logic |
| Adding the same destination GDB in multiple pallets | Supported (deduplication handles it), but verify intent |
| Storing network share credentials in pallet code | Use `<garage>/share/<name>.json` and `seat.map_network_drive()` |
| Calling `seat.map_network_drive()` without a credential file | The call will raise a `FileNotFoundError` — create the JSON file in the garage first |
| Expecting Cloud Logging without `roles/logging.logWriter` | The GCE service account must have this IAM role; initialization will fail gracefully but no logs reach GCL |
| Using `imp.load_source` in new code | Use `engine.load_module()` or `importlib.util` directly |
| Modifying `config.config_location` outside tests | Only set this in test `conftest.py` fixtures |

### 16.4 Testing Checklist for New Pallets

- [ ] Test `build()` with `"Production"`, `"Staging"`, and `"Dev"` configurations
- [ ] Test `validate_crate()` with valid and invalid data
- [ ] Test `process()` idempotency
- [ ] Provide a test GDB fixture in `tests/data/test_<module_name>/`
- [ ] Test `ship_on_fail` behavior if the pallet sets it to `True`
- [ ] Mock `seat.map_network_drive` in tests (avoid actual `net use` calls)
- [ ] Mock `is_running_on_gce` in `__main__` tests to control Cloud Logging

---

*This blueprint was regenerated on March 12, 2026 to reflect changes in forklift v9.7.4, including: `importlib.util` migration (ADR-006 resolved), Google Cloud Logging integration (ADR-007), `seat.map_network_drive()` utility (ADR-008), `RotatingFileHandler` adoption, and ship report now including `git_errors`. Regenerate this document after significant code changes by re-running the architecture-blueprint-generator skill.*
