"""
Hat PiFace under MicroPython -
Utlise module piface de https://github.com/mchobby/esp8266-upy/tree/master/hat-piface

Pi Hat              Pico
5V          2       VBUS    40
3.3V        1       3.3V    36
Gnd         6       Gnd     2
GPIO10 MOSI 19      GP11    SPI1-TX 15
GPIO9  MISO 21      GP8     SP1-RX  11
GPIO11 SCLK 23      GP10    SPI SCK 14
GPIO8  CS0  24      GP9     SPI-CS  12

"""

from machine import SPI, Pin, Timer
import json
import time
import ubinascii
import network

from umqttsimple import MQTTClient        # https://mpython.readthedocs.io/en/master/library/mPython/umqtt.simple.html
                                          # import mip; mip.install('https://raw.githubusercontent.com/micropython/micropython-lib/master/micropython/umqtt.simple/umqtt/simple.py') (nom simple.py à changer)
from piface import PiFace                 # import mip; mip.install("github:mchobby/esp8266-upy/hat-piface")

import config

led = Pin('LED', Pin.OUT)	# Pico Wifi

print("mqttpiface-pico.py")
led.on()
print("WIFI connection ...")

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(config.wifi_ssid, config.wifi_password)
while not wlan.isconnected():
 print(".", end='')
 time.sleep(1)
print(wlan.ifconfig())


mqttClient_id = ubinascii.hexlify(machine.unique_id())

lastPubMessage = 0
lastLedToggle = 0
pubInputInterval = 60

# Raspberry-picoW SPI1
spi = SPI(1, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(8))
cs = Pin(9, Pin.OUT, value=True )

print("INIT Piface ...")
piface = PiFace(spi, cs, device_id=0x00)

inputsState = [None, None, None, None, None, None, None, None ]
outputsState = config.initialOutputsState
state = { 'on': True, 'off': False}
outputType = { 'on': True, 'off': False}
inputsStateChange = False

counter = [0, 0, 0, 0, 0, 0, 0, 0]

# -----------------------------------------------------------------------------
# MQTT brocker connection
# -----------------------------------------------------------------------------
def mqtt_connect():
    if config.mqtt_broker_ca_file:
        try:
          # Using SSL
            f = open("ca.crt")
            ssl_data = f.read()
            f.close()
        except (OSError, IndexError) as exc:
            print("Failed to read CA file")
            publishMQTTmsg(config.mqttErrorTopic, 'Failed to read CA file', False)
            while True: pass
        client = MQTTClient(mqttClient_id, config.mqtt_broker_address, user=config.mqtt_broker_username, password=config.mqtt_broker_password, keepalive=60,ssl=True, ssl_params={'cert': ssl_data})
    else:
        # Not using SSL
        client = MQTTClient(mqttClient_id, config.mqtt_broker_address, user=config.mqtt_broker_username, password=config.mqtt_broker_password, keepalive=60)

    try:
        client.connect()
    except OSError as e:
        print('Failed to connected to MQTT Broker, Reset board')
        time.sleep(10)
        machine.reset()

    print(f"Connected to {config.mqtt_broker_address} MQTT Broker")
    return client

# -----------------------------------------------------------------------------
def on_message(topic, msg):
    print("MQTT msg received")
    print((topic, msg))
    outputstate = msg.decode('UTF-8')
    outputtopic = topic.decode('UTF-8')
    try:
        outputNum = int(outputtopic.split('/')[4])
    except ValueError:
        print(f"Failed to set output piface: output not in [0..7]")
        publishMQTTmsg(config.mqttErrorTopic, 'Failed to set output piface: output not in [0..7]', False)
        return
    if outputNum not in range( 0, 8 ):
        print(f"Failed to set output piface: output not in [0..7]")
        publishMQTTmsg(config.mqttErrorTopic, 'Failed to set output piface: output not in [0..7]', False)
        return
    if outputstate not in outputType:
        print(f"Failed to set output piface: state not in [on, off]")
        publishMQTTmsg(config.mqttErrorTopic, 'Failed to set output piface: state not in [on, off]', False)
        return
    outputsState[outputNum] = outputType[outputstate]
    piface.outputs[outputNum] = outputType[outputstate]
    publishMQTTmsg(config.mqttOutputTopic + str(outputNum), outputstate, False)

# -------------------------------------------------------------------------------------------------
def publishMQTTmsg(topic, payload, rflag):
    print("Publish MQTT topic %s = %s" % (topic, payload))
    try:
        mqttClient.publish(topic, payload, retain=rflag)
    except Exception as e:
        print("[MQTT] Publish ERROR: " + e.__str__())

# -----------------------------------------------------------------------------
def getInputsState(timer):
    for inputNum in range( 0, 8 ): 	# 0..7
        state = piface.inputs[inputNum] 
        if state != inputsState[inputNum]:
            publishMQTTmsg(config.mqttInputTopic + str(inputNum), 'on' if state else 'off', False)
            print(f"Input {inputNum} change to  {'on' if state else 'off'}")
            if inputNum in config.counterInputs:
                setCounter(inputNum, state)
            inputsState[inputNum] = state
        time.sleep_ms(10)

# -----------------------------------------------------------------------------
def setCounter(inputNum, state):
    if config.counterInputsMode[inputNum] == 'CHANGE':
        print("Input counter mode: CHANGE")
        counter[inputNum] += 1
    if not state and config.counterInputsMode[inputNum] == 'RISING':
        print("Input counter mode: RISING")
        counter[inputNum] += 1
    if state and config.counterInputsMode[inputNum] == 'FALLING':
        print("Input counter mode: FALLING")
        counter[inputNum] += 1
    print(f"Counter #{inputNum} = {counter[inputNum]}")
    publishMQTTmsg(config.mqttInputAttrTopic + str(inputNum), json.dumps({'counter': counter[inputNum]}), False)

# -----------------------------------------------------------------------------
def setOutputsState():
    for outputNum in range( 0, 8 ): 	# 0..7
        piface.outputs[outputNum] = outputsState[outputNum]
        time.sleep_ms(10)

# -------------------------------------------------------------------------------------------------
def initHomeassistantConfig():
    for outputNum in range( 0, 8 ): 	# 0..7
        configTopic = config.discovery_prefix + '/switch/picoface/output' + str(outputNum) + '/config'              # One switch per output
        # homeassistant/switch/pico-piface/output0/config
        configPayload = {
            'device': config.haDevice,
            'name': "Output " + str(outputNum),                                                 # Output 0
            'command_topic': config.mqttCmdTopic.decode().replace('#','') + str(outputNum),     # home/pico/piface/switch/0
            'unique_id': 'picoface_switch_output_' + str(outputNum),                            # picoface_switch_output_0
            'payload_on': 'on',
            'payload_off': 'off',
            'state_topic': config.mqttOutputTopic.decode() + str(outputNum),                    # home/pico/piface/output/0
            'state_on': 'on',
            'state_off': 'off',
            'retain': True
        }
        print(f"{configTopic}")
        publishMQTTmsg(configTopic, json.dumps(configPayload), True)

    for inputNum in range( 0, 8 ): 	# 0..7
        configTopic = config.discovery_prefix + '/binary_sensor/picoface/input' + str(inputNum) + '/config'              # One inary_sensor per input
        # homeassistant/binary_sensor/pico-piface/input0/config
        configPayload = {
            'device': config.haDevice,
            'name': "Input " + str(inputNum),                                                   # Input 0
            'state_topic': config.mqttInputTopic.decode() + str(inputNum),                      # home/pico/piface/input/0
            'unique_id': 'picoface_input_' + str(inputNum),                                     # picoface_input_0
            'force_update': True,
            'payload_on': 'off',
            'payload_off': 'on',
            'device_class': config.inputDeviceClasse,
            'expire_after': 600,
            'json_attributes_topic': config.mqttInputAttrTopic + str(inputNum),                 # home/pico/piface/counter/0
        }
        print(f"{configTopic}")
        publishMQTTmsg(configTopic, json.dumps(configPayload), True)

# -----------------------------------------------------------------------------
print('Connecting to %s MQTT brocker' % (config.mqtt_broker_address))
mqttClient = mqtt_connect()
mqttClient.set_callback(on_message)
mqttClient.subscribe(config.mqttCmdTopic)

if config.hommeassistant:           # With Homeassistant, switchs (outputs) statut are return with retain MQTT message
    initHomeassistantConfig()
else:
    setOutputsState()               # Without Homeassistant, init switch status with value in config

softTimer = Timer(mode=Timer.PERIODIC, period=200, callback=getInputsState)

print("Run Loop")
try:
    while True:
        if not wlan.isconnected():
            print('Wifi no longer connected, Reboot')
            time.sleep(10)
            machine.reset()

        mqttClient.check_msg()

        uptime = time.time()
        if (uptime - lastPubMessage) > pubInputInterval:
            print("Uptime: " + str(uptime))
            publishMQTTmsg(config.mqttUptimeTopic, str(uptime), False)
            for inputNum in range( 0, 8 ): 	# 0..7
                publishMQTTmsg(config.mqttInputTopic + str(inputNum), 'on' if inputsState[inputNum] else 'off', False)
                publishMQTTmsg(config.mqttInputAttrTopic + str(inputNum), json.dumps({'counter': counter[inputNum]}), False)
            inputsStateChange = False
            for outputNum in range( 0, 8 ): 	# 0..7
                publishMQTTmsg(config.mqttOutputTopic + str(outputNum), 'on' if outputsState[outputNum] else 'off', False)
            lastPubMessage = uptime

        if (uptime - lastLedToggle) > 2:
            led.toggle()
            lastLedToggle = uptime

except KeyboardInterrupt:
    softTimer.deinit()
    mqttClient.connect()
    piface.reset()
    print("Quitt")

