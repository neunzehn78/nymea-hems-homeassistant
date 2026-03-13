# Nymea HEMS – Home Assistant Integration

A custom Home Assistant integration for the **Consolinno Leaflet HEMS** system, communicating with the [Nymea](https://nymea.io) JSON-RPC API over TLS.

## Supported Hardware

This integration has been tested with the following setup:

| Device | Type |
|--------|------|
| bph WR1 / WR2 | PV inverter (Kaco) |
| BYD HVS 10.2 | Battery storage |
| hy-switch | Grid meter |
| Kaco Energy Meter | Energy meter |
| EPEX Day-Ahead | Electricity price source |
| SG Ready WP | Heat pump control |
| gridsupport | Grid support controller |

Any Nymea-based HEMS system should work in principle, but the energy calculations are tuned for Consolinno Leaflet setups.

## Features

- 🔌 Polls all devices and states from the Nymea server every 10 seconds
- ☀️ PV production sensors (power + energy) for each inverter
- 🔋 Battery state (SOC, charge/discharge power)
- ⚡ Grid import/export sensors
- 🏠 Calculated house consumption sensor
- 📊 Full Home Assistant Energy Dashboard compatibility
- 🔐 TLS connection with username/password authentication

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations → Custom repositories**
3. Add this repository URL and select category **Integration**
4. Search for "Nymea HEMS" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/nymea_hems` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "Nymea Energy Manager"
3. Enter your Nymea server details:

| Field | Description | Default |
|-------|-------------|---------|
| Host | IP address of your Nymea server | – |
| Port | TLS port | 2222 |
| Username | Nymea username | – |
| Password | Nymea password | – |

## Energy Dashboard Setup

After installation, configure the Energy Dashboard under **Settings → Energy**:

| Section | Sensor |
|---------|--------|
| Solar production (WR1) | `sensor.bph_wr1_totalenergyproduced` |
| Solar production (WR2) | `sensor.bph_wr2_totalenergyproduced` |
| Grid consumption | `sensor.hy_switch_totalenergyconsumed` |
| Grid return | `sensor.hy_switch_totalenergyproduced` |
| Battery charge | `sensor.total_battery_energy_charged` |
| Battery discharge | `sensor.total_battery_energy_discharged` |

For live power sensors, create two Template helpers (absolute value of `currentPower`) for each inverter.

## Calculated Sensors

The integration automatically creates these derived sensors under the **Energy System** device:

| Sensor | Description |
|--------|-------------|
| `sensor.energy_system_house_consumption` | Current house consumption (W) |
| `sensor.energy_system_pv_power` | Total PV production (W) |
| `sensor.energy_system_grid_import` | Power drawn from grid (W) |
| `sensor.energy_system_grid_export` | Power fed into grid (W) |
| `sensor.energy_system_battery_power` | Battery power (positive = discharging) |

## Requirements

- Home Assistant 2023.1.0 or newer
- Nymea server reachable on the local network (TLS, default port 2222)
- Consolinno Leaflet HEMS or compatible Nymea installation

## Known Limitations

- The integration polls the server every 10 seconds (configurable via `SCAN_INTERVAL` in `const.py`)
- EPEX `priceSeries` data (array of hourly prices) is not parsed – the sensor is present but shows raw data
- TLS certificate validation is disabled (self-signed certificates are common on local HEMS systems)

## License
CC BY-NC 4.0 – Non-commercial use only. See [LICENSE](LICENSE) for details.
