from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import SensorInfo, Sensor, DeviceInfo
import json
import time
import requests
import yaml
import sys
import logging
from yaml.loader import SafeLoader

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')


def unit_of_measurement(name):
    if (name.endswith("TmpVal")):
        return "°C"
    if (".W." in name):
        return "W"
    if (".TotWh" in name):
        return "Wh"
    if (name.endswith(".TotW")):
        return "W"
    if (name.endswith(".TotW.Pv")):
        return "W"
    if (name.endswith(".Watt")):
        return "W"
    if (".A." in name):
        return "A"
    if (name.endswith(".Amp")):
        return "A"
    if (name.endswith(".Vol")):
        return "V"
    if (name.endswith(".VA.")):
        return "VA"
    logging.debug("No unit of measurement for " + name)
    return ""

def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False

sensors = {}
def sendUpdate(name, uofm, mqtt_settings, device_info, value):
    sensor = sensors.get(name)
    if (sensor is None):
        sensor_info = SensorInfo(unit_of_measurement=uofm, 
                                name=name, 
                                device_class=None, 
                                unique_id=dev["serial"]+"-" + name, 
                                device=device_info)
        sensor = Sensor(Settings(mqtt=mqtt_settings, entity=sensor_info))
        sensors[name] = sensor
        time.sleep(0.1)
    print(">>>>>> " + name + " " + str(value))
    sensor.set_state(value)


with open('sma2mqtt.yaml') as f:
    cfg = yaml.load(f, Loader=SafeLoader)

loginurl = 'http://' + cfg["InverterAdress"] + '/api/v1/token'
postdata = {'grant_type': 'password',
         'username': cfg["InverterUsername"],
         'password': cfg["InverterPassword"],
         }

# Login & Extract Access-Token
try:
    x = requests.post(loginurl, data = postdata, timeout=5)
except requests.exceptions.ConnectTimeout:
    print("Inverter not reachable via HTTP.")
    print("Please test the following URL in a browser: " + 'http://' + cfg["InverterAdress"])
    sys.exit(1)
if ("Content-Length" in x.headers and x.headers["Content-Length"] == '0'):
    print("Username or Password wrong.")
    print("Please test the following URL in a browser: " + 'http://' + cfg["InverterAdress"])
    sys.exit(1)
token = x.json()["access_token"] 
headers = { "Authorization" : "Bearer " + token }

# Request Device Info
url="http://" + cfg["InverterAdress"] + "/api/v1/plants/Plant:1/devices/IGULD:SELF"
x = requests.get(url, headers = headers)
dev = x.json()

# Setup MQTT
mqtt_settings = Settings.MQTT(host=cfg["MqttServer"], 
                              username=cfg.get("MqttUser"), 
                              password=cfg.get("MqttPassword"),
                              discovery_prefix=cfg.get("MqttPrefix", "homeassistant") )
device_info = DeviceInfo(name=dev["product"], 
                         configuration_url='http://' + cfg["InverterAdress"], 
                         identifiers=dev["serial"], 
                         model = dev["vendor"]+"-" + dev["product"],
                         manufacturer = dev["vendor"],
                         sw_version = dev['firmwareVersion'])




exitafter = cfg.get("ExitAfter", None)
while exitafter is None or exitafter > 0:
    if exitafter: 
        exitafter -= 1
    try:
        url = 'http://' + cfg["InverterAdress"] + '/api/v1/measurements/live'
        x = requests.post(url, headers = headers, data='[{"componentId":"IGULD:SELF"}]')

        # Check if a new acccess token is neccesary (TODO use refresh token)
        if (x.status_code == 401):
            x = requests.post(loginurl, data = postdata)
            token = x.json()["access_token"] 
            headers = { "Authorization" : "Bearer " + token }
            continue
        
        data = x.json()

        for d in data:
            dname = d["channelId"].replace("Measurement.","").replace("[]", "")
            if "value" in d["values"][0]:
                v = d["values"][0]["value"]
                if isfloat(v):
                    v = round(v,2)
                sendUpdate(cfg.get("InverterPrefix", "") + dname, unit_of_measurement(dname), mqtt_settings, device_info,v);
            elif "values" in d["values"][0]:
                for idx in range(0, len(d["values"][0]["values"])):
                    v = d["values"][0]["values"][idx]
                    if isfloat(v):
                        v = round(v,2)
                    idxname = dname + "." + str(idx + 1)
                    sendUpdate(cfg.get("InverterPrefix", "") + idxname, unit_of_measurement(dname), mqtt_settings, device_info,v);
            else:
 
                # Value current not available // night?
                pass

        time.sleep(cfg["UpdateTimeSec"])
    except TimeoutError:
        pass

