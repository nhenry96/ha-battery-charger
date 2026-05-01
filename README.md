# Home Assistant Energy Manager

A Home Assistant configuration package for managing hybrid solar inverters, battery storage, and electricity costs. Supports multiple inverter brands via Modbus, dynamic and fixed electricity pricing, real-time MQTT telemetry, and Lovelace dashboards with optional Grafana integration.

**Current version:** `0.3.3`

---

## Table of Contents

- [Overview](#overview)
- [Supported Inverter Brands](#supported-inverter-brands)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Secrets](#secrets)
- [Directory Structure](#directory-structure)
- [Configuration](#configuration)
  - [Modbus](#modbus)
  - [Utility Meters](#utility-meters)
  - [Integrations (Packages)](#integrations-packages)
  - [Dashboards](#dashboards)
- [Automations](#automations)
- [Scripts](#scripts)
- [Helper Entities](#helper-entities)
- [Electricity Providers](#electricity-providers)
- [Updating Energy Manager](#updating-energy-manager)
- [Python Utilities](#python-utilities)
- [Custom Frontend Cards](#custom-frontend-cards)
- [Known Issues](#known-issues)

---

## Overview

This repo is a **Home Assistant "Energy Manager"** configuration focused on:

- Controlling hybrid inverters (battery charge/discharge modes, SOC limits, export limits, EMS mode) via **Modbus TCP**.
- Publishing unified inverter telemetry to **MQTT** regardless of brand, so dashboards and automations use consistent sensor names.
- Tracking 5-minute, hourly, daily, and monthly **import costs** and **export profits** for supported Australian electricity retailers (**Amber**, **LocalVolts**, **Flow Power**).
- Rolling up energy totals using **utility meters** and storing history in **InfluxDB**.
- Providing ready-made **Lovelace dashboards** for costs, PV, overview, and Grafana iframes.
- A self-contained **update mechanism** for the Energy Manager configuration itself.

---

## Supported Inverter Brands

| Brand | Modbus file | Status |
|-------|-------------|--------|
| **Sigenergy** | `modbus.yaml` (active default) | Active |
| Sungrow | `sungrow_modbus.yaml.disabled` | Switch-in |
| GoodWe | `goodwe_modbus.yaml.disabled` | Switch-in |
| Fronius | `fronius_modbus.yaml.disabled` | Switch-in |
| SolarEdge | `solaredge_modbus.yaml.disabled` | Switch-in |
| AlphaESS | `alphaess_modbus.yaml.disabled` | Switch-in |

To switch brands, change `input_select.inverter_brand` in the UI or use the `script.manual_activate_<brand>` scripts. The automation `inverter_brand_changed` will copy the correct `.disabled` file to `modbus.yaml` and flag a restart.

---

## Prerequisites

- **Home Assistant OS** or **Supervised** (Supervisor API used for updates and Grafana setup).
- **MQTT broker** (e.g. Mosquitto add-on).
- **InfluxDB** add-on (slug `a0d7b954-influxdb`, port 8086, database `home_assistant`).
- **Grafana** add-on (optional, slug `a0d7b954_grafana`) for Grafana dashboards.
- **Node-RED** (optional, port 1880) for MOTD mark-read endpoint.
- **Solcast Solar** integration for forecast data.
- **Modbus TCP** access to your inverter.

---

## Installation

1. Clone or copy this repo into your Home Assistant `/config` directory.
2. Create `secrets.yaml` (see [Secrets](#secrets) below).
3. Create an empty `scenes.yaml` (required by `configuration.yaml`):
   ```bash
   touch /config/scenes.yaml
   ```
4. Create a `themes/` directory or remove the `themes` frontend include from `configuration.yaml` if you have no themes.
5. Restart Home Assistant.

---

## Secrets

Create `/config/secrets.yaml` (gitignored) with the following keys:

```yaml
# Modbus inverter connection
modbus_host_ip: "192.168.x.x"
modbus_port: 502
modbus_slave: 1
```

Additional secrets may be required depending on your retailer and integrations (e.g. API keys for Amber or LocalVolts).

An example file is provided at `.env.example` (if present) for non-YAML secrets used by Python scripts.

### Environment variables (Python scripts)

| Variable | Used by | Purpose |
|----------|---------|---------|
| `SUPERVISOR_TOKEN` / `HASSIO_TOKEN` | `em_grafana_setup.py`, `perform_energy_manager_update.py` | Home Assistant Supervisor API authentication |

---

## Directory Structure

```
ha-battery-charger/
├── configuration.yaml          # Main HA config; includes all sub-files and packages
├── automations.yaml            # User automations + EM placeholder marker
├── scripts.yaml                # User scripts + EM placeholder marker
├── modbus.yaml                 # Active Modbus hub definition (default: Sigenergy)
├── *_modbus.yaml.disabled      # Inactive brand Modbus definitions
├── template.yaml               # User template sensors (additional PV power)
├── group.yaml                  # User groups + EM placeholder
├── utility_meter.yaml          # Energy and cost utility meter definitions
├── scenes.yaml                 # (Must be created manually — not in repo)
├── integrations/               # Energy Manager packages (auto-loaded)
│   ├── em_automations.yaml     # All EM automations
│   ├── em_scripts.yaml         # All EM scripts
│   ├── em_helpers.yaml         # Input helpers, shell commands, sensors, REST commands
│   ├── em_templates.yaml       # Template sensors, selects, binary sensors
│   ├── em_group.yaml           # EM entity groups
│   ├── mqtt_sensors.yaml       # MQTT sensor subscriptions
│   └── em_ui.yaml              # Lovelace dashboard registration + recorder excludes
├── dashboards/
│   ├── energy_manager_costs.yaml
│   ├── energy_manager_overview.yaml
│   ├── energy_manager_pv.yaml
│   └── grafana_energymanager.yaml
├── blueprints/                 # Standard HA blueprints (motion light, notify, etc.)
├── scripts/                    # Python utilities (updates, Grafana setup, entity fixes)
├── www/                        # /local frontend assets (custom cards, SVGs)
├── solcast_solar/              # Solcast JSON cache files
└── .energy_manager/            # EM version metadata and changelog
    └── version.txt             # Current version (e.g. 0.3.3)
```

---

## Configuration

### `configuration.yaml`

- Loads `default_config`.
- Includes `automations.yaml`, `scripts.yaml`, `scenes.yaml`, `modbus.yaml`, `utility_meter.yaml`, `template.yaml`, `group.yaml`.
- Loads all files under `integrations/` as **packages** (`!include_dir_named`).
- Configures **InfluxDB** (host `a0d7b954-influxdb`, port 8086, no SSL).
- Merges themes from `themes/` directory.

### Modbus

`modbus.yaml` defines a single TCP hub (`sigenergy_inverter`) connecting to `!secret modbus_host_ip:modbus_port`. It exposes holding and input registers for:

- Device info (model, firmware, serial)
- Energy totals (import, export, PV, battery charge/discharge)
- Real-time power flows (PCS, battery, grid, PV)
- State of charge and battery voltage/current
- EMS mode, charge/discharge mode, SOC limits
- Export and PV power limits

Alternate brand Modbus files (`*_modbus.yaml.disabled`) follow the same structure but are not loaded until activated.

### Utility Meters

Defined in `utility_meter.yaml`:

| Meter | Source | Cycle |
|-------|--------|-------|
| Grid import/export | EM 5m source sensors | 5 min, 15 min, hourly, daily, monthly, yearly |
| PV generation | EM 5m source sensors | daily, monthly, yearly |
| Battery charge/discharge | EM 5m source sensors | daily, monthly, yearly |
| Import cost | `sensor.em_import_cost_5m_source` | hourly, daily, monthly (`delta_values: true`) |
| Export profit | `sensor.em_export_profit_5m_source` | hourly, daily, monthly (`delta_values: true`) |

### Integrations (Packages)

All files in `integrations/` are loaded as HA packages:

| File | Domain keys |
|------|-------------|
| `em_automations.yaml` | `automation` |
| `em_scripts.yaml` | `script` |
| `em_helpers.yaml` | `shell_command`, `rest_command`, `sensor`, `binary_sensor`, `input_select`, `input_boolean`, `input_number`, `input_text`, `input_datetime`, `timer` |
| `em_templates.yaml` | `template` |
| `em_group.yaml` | `group` |
| `mqtt_sensors.yaml` | `mqtt` |
| `em_ui.yaml` | `lovelace`, `recorder` |

### Dashboards

| Dashboard | URL path | Description |
|-----------|----------|-------------|
| Energy Manager Costs | `/energy-manager-costs` | 5-minute and aggregated cost/profit tracking |
| Energy Manager Overview | `/energy-manager-overview` | Power flows, battery state, grid status |
| Energy Manager PV | `/em-inverter` | Inverter controls, mode selection, SOC limits |
| Grafana Energy Manager | `/grafana-energymanager` | Grafana iframe (adapts per retailer and viewport) |

Dashboards require the custom cards listed in [Custom Frontend Cards](#custom-frontend-cards).

---

## Automations

All EM automations are in `integrations/em_automations.yaml`. Key automations:

### Inverter Control

| Automation | Trigger | Action |
|-----------|---------|--------|
| `inverter_brand_changed` | `input_select.inverter_brand` state change | `script.switch_inverter_brand` |
| `sync_inverter_controls_on_startup` | HA start or brand change | Reads inverter registers and syncs input helpers |
| `inverter_ems_mode_changed` | EMS mode select change | `script.set_inverter_ems_mode` |
| `inverter_charge_discharge_mode_changed` | Charge/discharge select change | `script.set_inverter_charge_discharge_mode` |
| `inverter_run_mode_changed` | Run mode select change | Brand-specific start/stop register writes |
| `inverter_min/max_soc_changed` | SOC limit input changes | Matching `script.set_inverter_*` |
| `inverter_max/charge/discharge_power_changed` | Power limit input changes | Matching `script.set_inverter_*` |
| `inverter_export_power_limit_changed` | Export limit input change | `script.set_inverter_export_power_limit` |
| `inverter_export_power_limit_follow` | Every 20 s (Fronius only) | Dynamic export limit following house load |
| `check_inverter_connection` | `sensor.inverter_state` unavailable > 5 min | Persistent notification |
| `validate_safety_limits` | SOC/power limit exceeds safety cap | Persistent notification warning |

### Electricity Cost Tracking

| Automation | Trigger | Action |
|-----------|---------|--------|
| `electricity_5_minute_import_cost_export_price` | Every minute at second 02, every 5 minutes | Compute 5-minute import cost and export profit for selected provider |
| `electricity_import/export_*_reset` | Hourly/daily/monthly time patterns | Zero the corresponding cost/profit input_numbers |

### Energy Manager Updates

| Automation | Trigger | Action |
|-----------|---------|--------|
| `energy_manager_scheduled_update_check` | Daily at 06:00 | `shell_command.check_energy_manager_updates`; notify if update available |
| `energy_manager_manual_update_check` | Manual trigger | Same check with detailed notifications |
| `energy_manager_perform_update` | Manual trigger (update available) | `shell_command.perform_energy_manager_update` |

### Other

| Automation | Trigger | Action |
|-----------|---------|--------|
| `solcast_update` | Daily at 05:00 | `solcast_solar.update_forecasts` |
| `create_inverter_mqtt_sensors` | HA start | MQTT discovery publish for all inverter topics |
| `publish_inverter_data_to_mqtt` | Every 10 s | `script.publish_inverter_data` |
| `restart_reminder` | Every 30 min | Notify if `input_boolean.restart_required` is on |
| `restore_inverter_brand_on_startup` | HA start | Restore saved inverter brand selection after 5 s delay |
| `save_inverter_brand_selection` | Brand select change | Copy to `input_text.saved_inverter_brand` |
| `flowpower_peak_enable/disable` | Configured peak window datetimes | Toggle `input_boolean.flowpower_in_peak` |
| `sellbuy_mode_enabled` / `highsell_mode_enabled` | Respective boolean on | Mutual exclusion: turns the other off |
| `em_grafana_first_boot` | HA start | `shell_command.em_grafana_setup` |
| `generate_ssh_key_shell` | Manual only | Generate SSH key; store public key in `input_text` |

---

## Scripts

All EM scripts are in `integrations/em_scripts.yaml`:

| Script | Purpose |
|--------|---------|
| `switch_inverter_brand` | Copy brand's `.disabled` Modbus file to `modbus.yaml`, notify, flag restart |
| `manual_activate_<brand>` | Per-brand version of the above (7 scripts) |
| `set_inverter_ems_mode` | Write EMS mode register per brand |
| `set_inverter_charge_discharge_mode` | Write charge/discharge mode registers (all brands) |
| `set_inverter_min_soc` / `max_soc` / `reserved_soc_backup` | SOC limit register writes |
| `set_inverter_charge_discharge_power` / `max_charge_power` / `max_discharge_power` | Power limit register writes |
| `set_inverter_pv_power_limit` | PV output limit register writes |
| `set_inverter_export_power_limit` | Export limit Modbus/MQTT writes (includes Fronius dynamic) |
| `set_inverter_export_power_limit_enabled` | Toggle export limiting per brand |
| `publish_inverter_data` | Publish all inverter telemetry to MQTT `homeassistant/sensor/inverter/*/state` |
| `goodwe_eh_reset_all_8slots` / `goodwe_reset_all_4slots` | Clear GoodWe time-of-use schedule registers |
| `debug_modbus_files` | Shell list of Modbus files + notification |
| `check_config_status` | Shell status listing + notification |
| `notify_restart_needed` | Generic persistent restart notification |
| `check_for_energy_manager_updates` | Trigger manual update check automation |
| `update_energy_manager` / `update_energy_manager_force` | Run EM update shell commands |

---

## Helper Entities

### `input_select`

| Entity | Options / Purpose |
|--------|-------------------|
| `input_select.inverter_brand` | Sigenergy, Sungrow, GoodWe, Fronius, SolarEdge, AlphaESS, unknown |
| `input_select.inverter_ems_mode` | Self-consumption, Feed-in priority, Backup, etc. (brand-specific) |
| `input_select.inverter_charge_discharge_mode` | Auto, Force charge, Force discharge, etc. |
| `input_select.inverter_run_mode` | Start / Stop |
| `input_select.electricity_provider` | Amber, LocalVolts, Flow Power |
| `input_select.flowpower_charge_limit_tier` | Flow Power charge limit tiers |

### `input_number`

| Entity | Purpose |
|--------|---------|
| `input_number.inverter_min_soc` | Minimum battery SOC (%) |
| `input_number.inverter_max_soc` | Maximum battery SOC (%) |
| `input_number.inverter_reserved_soc_backup` | Backup reserve SOC (%) |
| `input_number.inverter_charge_discharge_power` | Charge/discharge power setpoint (W) |
| `input_number.inverter_max_charge_power` | Maximum charge power cap (W) |
| `input_number.inverter_max_discharge_power` | Maximum discharge power cap (W) |
| `input_number.inverter_max_power_limit` | Overall inverter output limit (W) |
| `input_number.inverter_export_power_limit` | Grid export limit (W) |
| `input_number.inverter_pv_power_limit` | PV output limit (W) |
| `input_number.electricity_import_cost_*` | Running import cost (5m / hourly / daily / monthly) |
| `input_number.electricity_export_profit_*` | Running export profit (5m / hourly / daily / monthly) |
| `input_number.curtail_cents` | Curtailment price threshold (c/kWh) |
| `input_number.ascore_*` / `input_number.pscore_*` | Amber/Plan scoring weights |
| Flow Power tariff fields | Peak/off-peak/feed-in rates, supply charge, etc. |
| GoodWe slot selectors | Time-of-use schedule slot configuration |

### `input_boolean`

| Entity | Purpose |
|--------|---------|
| `input_boolean.restart_required` | Flags that HA needs a restart |
| `input_boolean.inverter_export_power_limit_enabled` | Enable/disable export limiting |
| `input_boolean.sigenergy_remote_ems_auto` | Sigenergy remote EMS auto mode |
| `input_boolean.sellbuy_mode_enabled` | Sell-buy arbitrage mode |
| `input_boolean.high_sell_price_toggle` | High sell price mode (mutually exclusive with sellbuy) |
| `input_boolean.flowpower_in_peak` | Flow Power currently in peak window |
| `input_boolean.energy_manager_update_available` | Update check result flag |
| `input_boolean.energy_control_auto_reenable` | Auto re-enable energy control after timer |
| `input_boolean.em_api_enabled` | Enable EM API decision sensor |

### `input_text`

| Entity | Purpose |
|--------|---------|
| `input_text.saved_inverter_brand` | Persists brand selection across restarts |
| `input_text.energy_control_duration` | Timer duration for energy control (HH:MM:SS) |
| `input_text.price_signal` | Price signal string for plan scoring |
| `input_text.aemo_region` | AEMO region code |
| `input_text.ssh_public_key` | Stored SSH public key |

### `timer`

| Entity | Purpose |
|--------|---------|
| `timer.energy_control` | Auto-disable/re-enable energy control switch |

---

## Electricity Providers

Select provider via `input_select.electricity_provider`. The `electricity_5_minute_import_cost_export_price` automation handles each:

### Amber / LocalVolts (dynamic pricing)

- Every 5 minutes, computes energy delta from `sensor.grid_import_total` / `sensor.grid_export_total`.
- Multiplies by `sensor.grid_buy_price` / `sensor.grid_sell_price` (provided by Amber/LocalVolts integration).
- Accumulates into `input_number.electricity_import/export_cost_5m`.

### Flow Power (fixed / time-of-use)

- Uses `sensor.flowpower_buy_price` and configured peak/off-peak/feed-in rates from `input_number` helpers.
- `input_boolean.flowpower_in_peak` is toggled by `flowpower_peak_enable/disable` automations based on `input_datetime` peak window.

---

## Updating Energy Manager

### Automatic (daily at 06:00)

If `input_boolean.energy_manager_auto_check_updates` is on, a shell script checks for updates. A persistent notification is created if a new version is available.

### Manual

1. In the EM dashboard, use the **Check for Updates** button (triggers `script.check_for_energy_manager_updates`).
2. If an update is available, use the **Update Energy Manager** button.

The update process is handled by `scripts/perform_energy_manager_update.py`, which merges new configuration while preserving user-defined blocks (marked by `=== ENERGY_MANAGER_AUTOMATIONS_START/END ===` markers in `automations.yaml`).

Version metadata is stored in `.energy_manager/version.txt`.

---

## Python Utilities

Located in `scripts/`:

| Script | Purpose |
|--------|---------|
| `check_energy_manager_updates.py` | Check GitHub for new EM version; writes update status to `.energy_manager/` |
| `perform_energy_manager_update.py` | Download and merge updated EM config; preserves user blocks; uses Supervisor API |
| `em_grafana_setup.py` | First-boot Grafana datasource/dashboard setup via Supervisor token |
| `entity_manager.py` | Entity registry utilities |
| `fix_entity_registry_and_restart.py` | Fix entity registry issues and trigger restart |
| `file_merger.py` | YAML file merge helper for update process |
| `update_checker.py` | Supporting module for version comparison |

---

## Custom Frontend Cards

The following custom cards are bundled under `www/` and loaded as `/local` resources:

- `layout-card` — flexible layout for dashboards
- `apexcharts-card` — charting
- `card-mod` — CSS card customization
- `mod-card` — card modifier
- `state-switch` — conditional card display
- `energy-flow` card — power flow visualization
- `platinum-weather-card` — weather display

These are loaded automatically by Home Assistant from `www/`. No manual resource registration is required beyond what `em_ui.yaml` sets up.

---

## Known Issues

1. **`scenes.yaml` missing** — `configuration.yaml` includes it but no file exists. Create an empty one before first boot.
2. **`themes/` directory missing** — frontend theme merge will warn/error if no themes folder exists.
3. **Typo in `sync_inverter_controls_on_startup`** — brand condition uses `solaredege` instead of `solaredge`; SolarEdge controls may not sync on startup.
4. **`electricity_dashboard.py`** — referenced in a `shell_command` but not included in this repo (expected on a running HA `/config`).
5. **Duplicate automation markers** — `automations.yaml` contains duplicate `# === ENERGY_MANAGER_AUTOMATIONS_END ===` markers which may affect the update merge logic.
6. **`input_number` vs `utility_meter` naming** — hourly reset automations target `input_number.electricity_import_cost_hourly` but the equivalent utility meter creates `sensor.electricity_import_cost_hourly`; these are different domains.
