\# Niko Energy Integration for Home Assistant



!\[Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-blue)



This custom component allows Home Assistant to read live \*\*power (Watt)\*\* and \*\*energy (kWh)\*\* data from a \*\*Niko Home Control (NHC)\*\* system using a TCP socket connection.



It provides:



\- Real-time power readings (W) - sensor

\- Automatically calculated energy usage (kWh) - sensor

\- Integration into the Home Assistant Energy dashboard

\- Lightweight and fully local (no cloud needed)



---



\## ⚙️ Installation



\### Manual



1\. Copy the "niko\_energy" folder from this repository to:



/config/custom\_components/niko\_energy/



2\. Restart Home Assistant.



3\. Go to \*\*Settings > Devices \& Services > Integrations\*\*, click \*\*Add Integration\*\*, and search for `Niko Homecontrol I Energy Monitor`.



\## 🧠 Configuration



This integration requires:



\- IP address of your Niko controller (on the local network)

\- TCP port (usually `8000`)

\- List of channel IDs and names you want to track (auto discovered)



Once added, the integration will:



* Start a live TCP stream
* Request live power data (getlive)
* Calculate cumulative kWh from the stream over time



| Entity Type   | Unit  | State Class      | Updates            |

| ------------- | ----- | ---------------- | ------------------ |

| Power Sensor  | `W`   | Measurement      | Push               |

| Energy Sensor | `kWh` | Total Increasing | Derived from power |



You can safely add the energy sensors to the Energy Dashboard.



