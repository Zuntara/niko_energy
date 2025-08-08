# Niko Home Control I Energy Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.6+-blue)](https://www.home-assistant.io/)

This custom component allows Home Assistant to read live **power (Watt)** and **energy (kWh)** data from a **Niko Home Control (NHC) I** system using a TCP socket connection.

It provides:

- Real-time power readings (W) - sensor
- Automatically calculated energy usage (kWh) - sensor
- Integration into the Home Assistant Energy dashboard
- Lightweight and fully local (no cloud needed)
- Configuration screen for IP and Port of NHC I controller and configuration for channels

---

## ⚙️ Installation

### Manual

1. Copy the "niko_energy" folder from this repository to: `/config/custom_components/niko_energy/`
2. Restart Home Assistant.
3. Go to **Settings > Devices & Services > Integrations**, click **Add Integration**, and search for `Niko Homecontrol I Energy Monitor`.

### Automatic

[![Add to HACS](https://img.shields.io/badge/Add%20to%20HACS-Custom%20Repository-blue?logo=home-assistant&style=for-the-badge)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Zuntara&repository=niko_energy&category=integration)

## 🧠 Configuration

This integration requires:

- IP address of your Niko controller (on the local network)
- TCP port (usually `8080`)
- List of channel IDs and names you want to track (auto discovered)

Once added, the integration will:

* Start a live TCP stream
* Request live power data (getlive)
* Calculate cumulative kWh from the stream over time

| Entity Type   | Unit  | State Class      | Updates            |
| ------------- | ----- | ---------------- | ------------------ |
| Power Sensor  | `W`   | Measurement      | Push               |
| Energy Sensor | `kWh` | Total Increasing | Derived from power |

You can safely add the energy sensors to the Energy Dashboard.

![Example of Niko Energy Dashboard](https://github.com/Zuntara/niko_energy/blob/main/images/Screenshot%202025-08-08%20104909.png)

