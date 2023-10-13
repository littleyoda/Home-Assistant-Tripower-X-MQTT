from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import SensorInfo, Sensor, DeviceInfo
import json
import time
import requests
import yaml
import sys
import logging
import threading
import socket
import struct

from yaml.loader import SafeLoader
from speedwiredecoder import decode_speedwire

import urllib3

urllib3.disable_warnings()

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.WARNING,
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
def sendUpdate(name, unique_id, uofm, mqtt_settings, device_info, value):
    sensor = sensors.get(name)
    if (sensor is None):
        sensor_info = SensorInfo(unit_of_measurement=uofm, 
                                name=name, 
                                device_class=None,
                                unique_id=unique_id, 
                                device=device_info)
        sensor = Sensor(Settings(mqtt=mqtt_settings, entity=sensor_info))
        sensors[name] = sensor
        time.sleep(0.1)
    sensor.set_state(value)


def updateTripower(cfg, mqtt_settings):
    logging.warning("Starting Tripower-X Thread")
    loginurl = 'https://' + cfg["Address"] + '/api/v1/token'
    postdata = {'grant_type': 'password',
            'username': cfg["Username"],
            'password': cfg["Password"],
            }

    # Login & Extract Access-Token
    try:
        x = requests.post(loginurl, data = postdata, timeout=5, verify=False)
    except requests.exceptions.ConnectTimeout:
        print("Inverter not reachable via HTTP.")
        print("Please test the following URL in a browser: " + 'https://' + cfg["Address"])
        sys.exit(1)
    if ("Content-Length" in x.headers and x.headers["Content-Length"] == '0'):
        print("Username or Password wrong.")
        print("Please test the following URL in a browser: " + 'https://' + cfg["Address"])
        sys.exit(1)
    token = x.json()["access_token"] 
    headers = { "Authorization" : "Bearer " + token }

    # Request Device Info
    url="https://" + cfg["Address"] + "/api/v1/plants/Plant:1/devices/IGULD:SELF"
    x = requests.get(url, headers = headers, verify=False)
    dev = x.json()

    device_info = DeviceInfo(name=dev["product"], 
                            configuration_url='https://' + cfg["Address"], 
                            identifiers=dev["serial"], 
                            model = dev["vendor"]+"-" + dev["product"],
                            manufacturer = dev["vendor"],
                            sw_version = dev['firmwareVersion'])




    exitafter = cfg.get("ExitAfter", None)
    while exitafter is None or exitafter > 0:
        if exitafter: 
            exitafter -= 1
        try:
            url = 'https://' + cfg["Address"] + '/api/v1/measurements/live'
            x = requests.post(url, headers = headers, data='[{"componentId":"IGULD:SELF"}]', verify=False)

            # Check if a new acccess token is neccesary (TODO use refresh token)
            if (x.status_code == 401):
                x = requests.post(loginurl, data = postdata, verify=False)
                token = x.json()["access_token"] 
                headers = { "Authorization" : "Bearer " + token }
                continue
            
            data = x.json()

            for d in data:
                dname = cfg.get("SensorPrefix", "") + d["channelId"].replace("Measurement.","").replace("[]", "")
                if "value" in d["values"][0]:
                    v = d["values"][0]["value"]
                    if isfloat(v):
                        v = round(v,2)
                    sendUpdate( dname, dev["serial"]+"-" + dname, unit_of_measurement(dname), mqtt_settings, device_info,v);
                elif "values" in d["values"][0]:
                    for idx in range(0, len(d["values"][0]["values"])):
                        v = d["values"][0]["values"][idx]
                        if isfloat(v):
                            v = round(v,2)
                        idxname = dname + "." + str(idx + 1)
                        sendUpdate(idxname,  dev["serial"]+"-" + idxname, unit_of_measurement(dname), mqtt_settings, device_info,v);
                else:
    
                    # Value current not available // night?
                    pass


            time.sleep(cfg["UpdateTimeSec"])
        except TimeoutError:
            pass


def updatePowerMeter(cfg, mqtt_settings):
    logging.warning("Starting Energie-Meter Thread")
    MCAST_GRP = '239.12.255.254'
    MCAST_PORT = 9522
    IPBIND = '0.0.0.0'

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", MCAST_PORT))
    try:
        mreq = struct.pack("4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton(IPBIND))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except BaseException:
        logging.CRITICAL("Could not connect to multicast/Tripower-Xinterface")
        sys.exit(1)
    deviceInfos = {}
    oldTime = 0
    while True:
        emdata=decode_speedwire(sock.recv(608))
        if (emdata.get("protocol",0) not in [0x6069] or emdata.get("serial") is None):
            continue
        if time.time() - oldTime < cfg.get("UpdateTimeSec",10):
            continue
        oldTime = time.time()
        print("next")
        # Take care of case with more than one energy meter
        if (not deviceInfos.get(emdata["serial"])):
            deviceInfos[emdata["serial"]] = DeviceInfo(name="SMA Energy Meter / Sunny Home Manager (2)", 
#                            configuration_url='http://' + cfg["InverterAdress"], 
                            identifiers=emdata["serial"], 
                            model = "EM/SHM/SHM2",
                            manufacturer = "SMA",
                            sw_version = emdata['speedwire-version'])
        deviceInfo = deviceInfos[emdata["serial"]]

        for key, value in emdata.items():
            if (key.endswith("unit") or key in ["serial", "protocol", "speedwire-version"]):
                continue

            if "consume" in key or "supply" in key or key in ["cosphi","frequency","i1","u1","cosphi1","i2","u2","cosphi2","i3","u3","cosphi3"]:
                sendUpdate("shm2-" + key, str(emdata["serial"])+"-" + key, 
                           unit_of_measurement(key), 
                           mqtt_settings, 
                           deviceInfo,
                           value)
            else:
                print(key)
            # device_info = DeviceInfo(name=dev["product"], 
            #                 configuration_url='http://' + cfg["InverterAdress"], 
            #                 identifiers=dev["serial"], 
            #                 model = dev["vendor"]+"-" + dev["product"],
            #                 manufacturer = dev["vendor"],
            #                 sw_version = dev['firmwareVersion'])



cfgfile = 'sma2mqtt.yaml' if (len(sys.argv) == 1)  else sys.argv[1]
print(cfgfile)
print(sys.argv)
with open(cfgfile) as f:
    cfg = yaml.load(f, Loader=SafeLoader)

# Setup MQTT
mqtt_settings = Settings.MQTT(host=cfg["Mqtt"]["Server"], 
                            username=cfg["Mqtt"].get("User"), 
                            password=cfg["Mqtt"].get("Password"),
                            discovery_prefix=cfg["Mqtt"].get("Prefix", "homeassistant") )

# Prepare all Threads
threads=[]
for dev in cfg["Devices"]:
    if (dev["Type"].lower() == "tripowerx"):
        tripower = threading.Thread(target=updateTripower, args=[dev,mqtt_settings])
        threads.append(tripower)
    elif (dev["Type"].lower() in ["em","shm","shm2"]):
        powermeter = threading.Thread(target=updatePowerMeter, args=[dev,mqtt_settings])
        threads.append(powermeter)
    else:
        logging.critical("Device Type " + dev["Type"] + " unknown!")
        sys.exit(1)

# Start all Threads
for thread in threads:
    thread.start()

# Wait for Threads to finish
for thread in threads:
    thread.join()
