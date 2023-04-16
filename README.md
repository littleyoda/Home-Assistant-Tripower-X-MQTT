# Home-Assistant-Tripower-X-MQTT

Script which reads out the current measured values of an inverter of the [SMA Tripower x (STP XX-50)](https://www.sma.de/produkte/solar-wechselrichter/sunny-tripower-x) series and makes them available via MQTT to Home Assistant.
For other inverter and even for other SMA inverter series, the script will most likely not work.

Optionally, the measured values from [SMA Energy Meter](https://www.sma.de/produkte/monitoring-control/sma-energy-meter) or [Sunny Home Manager](https://www.sma.de/produkte/monitoring-control/sunny-home-manager) can also be received and makes them also available via MQTT to Home Assistant.

Home Assistant detects the sensors automatically via [MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery).

The Python script is a _proof of concept_. I have been using the script myself for a few successful weeks now.

The script cannot currently be executed as an add-on or similar in Home Assistant. It has to be started manually on a computer with installed Python.

Most values from the Tripower-X Inverter are only returned if the PV system also produces electricity. At times when no electricity is produced, only a fraction of the measured values are returned.

## Supported Devices

* SMA Sunny Tripower X 12 / 15 / 20 / 25
* Sunny Home Mananger (2)
* SMA Energy Meter

## Technical background

* Tripower X: The script accesses the web interface of the inverter via HTTP. It requests the measured values via JSON
* Energy Meter/Sunny Home Manager: regularly sends the data to the local network via multicast. These data packets are received and processed.

## Usage
To install the libraries necessary for the script, the following instruction must be executed.
      pip install -r requirements.txt

For use, an MQTT server (e.g. [Mosquitto broker Add-On](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md)) must be running and the [MQTT integration](https://www.home-assistant.io/integrations/mqtt) in Home Assistant must be active.

The config file (sma2mqtt.yaml) must be changed before use.
  
## Future
Since the script works for me, I will probably not invest any more time. However, I am open to pull requests.
It would be nice if someone could turn the script into a home assistant integration.


## Images
![](https://raw.githubusercontent.com/littleyoda/Home-Assistant-Tripower-X-MQTT/main/images/inverter.png)
![](https://raw.githubusercontent.com/littleyoda/Home-Assistant-Tripower-X-MQTT/main/images/ha.png)
