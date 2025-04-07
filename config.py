# mqttpiface-pico config file
# you may edit this file by hand

"""
26/2/2023
1ière version
"""

# WIFI access details
wifi_ssid = '<my_ap>'
wifi_password = '<my_ap_password>'
wifi_country = 'FR'

# MQTT broker settings
mqtt_broker_address = '@IP'
mqtt_broker_username = 'xxxx'
mqtt_broker_password = 'yyyy'
# mqtt broker if using local SSL, copy a ca.crt to pico
mqtt_broker_ca_file = None

# MQTT topics
mqttCmdTopic = b'home/pico/piface/switch/#'                   # Topic to control output: mosquitto_pub -h mqttbrocker -t "home/pico/piface/switch/0" -m on -r
mqttUptimeTopic = b'home/pico/piface/sys/uptime'
mqttErrorTopic = b'home/pico/piface/sys/error'
mqttInputTopic = b'home/pico/piface/input/'                   # home/pico/piface/input/1            off       1 = input number  [0..7]
mqttOutputTopic = b'home/pico/piface/output/'                 # home/pico/piface/output/2           on        2 = output number [0..7]
mqttInputAttrTopic = b'home/pico/piface/inputattributs/'      # home/pico/piface/inputattributs/0   {'counter' = 0}

# home-assistant config
hommeassistant = True
discovery_prefix = 'homeassistant'
haDevice = {
                'identifiers': ['picoface'],                    # Commun aux entities du device
                'manufacturer':'PiFace',
                'model': "V1",
                'name': 'PicoFace',
                'sw_version': "24/08/2024"
            }
inputDeviceClasse = 'opening'

# outpout state on reboot
initialOutputsState = [False, False, False, False, False, False, False, False ]

# Initialize inputs counter
counterInputs = [1,3]
counterInputsMode = ['FALLING', 'FALLING', 'FALLING', 'RISING', 'FALLING', 'FALLING', 'FALLING', 'FALLING']    # RISING, FALLING, CHANGE


