from ha_mqtt_discoverable.device import Device
import json
import time
import requests
import yaml
from yaml.loader import SafeLoader


def unit_of_measurement(name):
    if (name.endswith("TmpVal")):
        return "°C"
    if (".W." in name):
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
    print(name)
    return ""

def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False




with open('sma2mqtt.yaml') as f:
    cfg = yaml.load(f, Loader=SafeLoader)
    print(cfg)

loginurl = 'http://' + cfg["InverterAdress"] + '/api/v1/token'
postdata = {'grant_type': 'password',
         'username': cfg["InverterUsername"],
         'password': cfg["InverterPassword"],
         }

# Login & Extract Access-Token
x = requests.post(loginurl, data = postdata, timeout=5)
print(x.text)
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


while True:
    url = 'http://' + cfg["InverterAdress"] + '/api/v1/measurements/live'
    x = requests.post(url, headers = headers, data='[{"componentId":"IGULD:SELF"}]')
    # Check if a new acccess token is neccesary (TODO use refresh token)
    if (x.status_code == 401):
        x = requests.post(loginurl, data = postdata)
        token = x.json()["access_token"] 
        headers = { "Authorization" : "Bearer " + token }
        continue
    
    print(x.text)
    print(x.status_code)
    data = x.json()

    for d in data:
        print(d)
        dname = d["channelId"].replace("Measurement.","").replace("[]", "")
        if "value" in d["values"][0]:
            print("Single")
            v = d["values"][0]["value"]
            if isfloat(v):
                v = round(v,2)
            print(dname + ": " + str(v))
            device.add_metric(
                name= dname,
                value=v,
                configuration={"name": dname},
                unit_of_measurement = unit_of_measurement(dname)
            )
        elif "values" in d["values"][0]:
            print("Multi")
            for idx in range(0, len(d["values"][0]["values"])):
                v = d["values"][0]["values"][idx]
                if isfloat(v):
                    v = round(v,2)
                idxname = dname + "." + str(idx + 1)
                print(idxname + ": " + str(v))
                device.add_metric(
                    name= idxname,
                    value=v,
                    configuration={"name": idxname} ,
                    unit_of_measurement = unit_of_measurement(dname)
                )
        else:
            # Value current not available // night?
            pass

    device.publish()
    time.sleep(cfg["UpdateTimeSec"])


