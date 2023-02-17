# Home-Assistant-Tripower-X-MQTT

Script which reads out the current measured values of an inverter of the [SMA Tripower x (STP XX-50)](https://www.sma.de/produkte/solar-wechselrichter/sunny-tripower-x) series and makes them available via MQTT Home Assistant.
For other inverter and even for other SMA inverter series, the script will most likely not work.

The Python script is a _proof of concept_. I have been using the script myself for a few successful weeks now.

The script cannot currently be executed as an add-on or similar in Home Assistant. It has to be started manually on a computer with installed Python.
  
## Usage
The following packages are required: 
* ha-mqtt-discoverable 
* pyyaml

      pip install ha-mqtt-discoverable pyyaml

The script accesses the web interface of the inverter. It extracts the displayed measured values at regular intervals and transfers them to Home Assistant via [MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery).

The config file (sma2mqtt.yaml) must be changed before use.
  
## Future
Since the script works for me, I will probably not invest any more time. However, I am open to pull requests.
It would be nice if someone could turn the script into a home assistant integration.


## Images
![](https://raw.githubusercontent.com/littleyoda/Home-Assistant-Tripower-X-MQTT/main/images/inverter.png)
![](https://raw.githubusercontent.com/littleyoda/Home-Assistant-Tripower-X-MQTT/main/images/ha.png)
