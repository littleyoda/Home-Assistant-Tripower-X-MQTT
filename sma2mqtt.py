from ha_mqtt_discoverable.device import Device
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

# Configure Device for ha_mqtt_discoverable
configd = {
    "mqtt_server": cfg["MqttServer"],
    "mqtt_prefix": cfg["MqttPrefix"],
    "mqtt_user": cfg["MqttUser"],
    "mqtt_password": cfg["MqttPassword"],
    "device_id": dev["serial"],
    "device_name": dev["product"],
    "device_class":"None",
    "manufacturer": dev["vendor"],
    "model": dev["vendor"]+"-" + dev["product"],
    "client_name": "sma2mqtt" + str(dev["serial"]),
    "unique_id": dev["vendor"]+"-" + dev["product"] + "-" + str(dev["serial"])
}
device = Device(settings=configd)

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
                device.add_metric(
                    name= dname,
                    value=v,
                    configuration={"name": dname},
                    unit_of_measurement = unit_of_measurement(dname)
                )
            elif "values" in d["values"][0]:
                for idx in range(0, len(d["values"][0]["values"])):
                    v = d["values"][0]["values"][idx]
                    if isfloat(v):
                        v = round(v,2)
                    idxname = dname + "." + str(idx + 1)
                    device.add_metric(
                        name= idxname,
                        value=v,
                        configuration={"name": idxname} ,
                        unit_of_measurement = unit_of_measurement(dname)
                    )
            else:
                # Value current not available // night?
                pass

        logging.info("Publishing to Home Assistant")
        device.publish()
        time.sleep(cfg["UpdateTimeSec"])
    except TimeoutError:
        pass

