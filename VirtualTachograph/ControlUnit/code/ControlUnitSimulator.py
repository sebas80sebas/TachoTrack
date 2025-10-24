import threading
import socket
import json
import time
import datetime
import os
import random
import paho.mqtt.client as mqtt
from GracefulKiller import GracefulKiller

monitor = GracefulKiller()

# Global system state
current_state = {
    "tachograph_id": None,
    "Position": None,
    "GPSSpeed": 0.0,
    "Speed": 0.0,
    "driver_present": "None",
    "Timestamp": 0
}

# Lists to store telemetry and event logs
logs_telemetry = []
logs_event = []

# Thread synchronization locks
lock_telemetry = threading.Lock()
lock_event = threading.Lock()
lock_current_state = threading.Lock()

# Control flags
state_changed = False
last_time = 0
connection_granted = False

# Generate random tachograph ID and set it in current state
tachograph_id = "tachograph_control_unit-" + str(random.randint(1, 5))
current_state["tachograph_id"] = tachograph_id

# Configuration parameters
telemetry_frequency = 1  # Telemetry sending frequency (seconds)
odometer_gnss_frequency = 1  # Sensor sampling frequency (seconds)

def get_host_name():
    """Get container hostname from environment"""
    return os.getenv("HOSTNAME")

def client_listener_card_reader(connection, address):
    """
    Handle card reader connections.
    Processes card insertion/removal events.
    """
    print(f"{datetime.datetime.now()} - New connection {connection} {address}")

    while not monitor.kill_now:
        data = connection.recv(1024)
        if not data:
            break
        else:
            data = data.decode("utf-8")
            print(f"{datetime.datetime.now()} - Received message: {data}")
            process_received_message(data)
            connection.sendall(bytes("ok-" + str(time.time()), "utf-8"))

def client_listener_positioning_system(connection, address):
    """
    Handle GNSS positioning system connections.
    Processes location and GPS speed data.
    """
    global odometer_gnss_frequency
    print(f"{datetime.datetime.now()} - New connection {connection} {address}")
    
    while not monitor.kill_now:
        data = connection.recv(1024)
        if not data:
            break
        else:
            data = data.decode("utf-8")
            print(f"{datetime.datetime.now()} - Received message: {data}")
            process_received_message(data)
            # Send sampling frequency to GNSS
            new_frequency_message = {
                "new_gnss_frequency": odometer_gnss_frequency,
                "timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
                }
            connection.sendall(bytes(json.dumps(new_frequency_message), "utf-8"))

def client_listener_odometer(connection, address):
    """
    Handle odometer connections.
    Processes vehicle speed data.
    """
    global odometer_gnss_frequency
    print(f"{datetime.datetime.now()} - New connection {connection} {address}")

    while not monitor.kill_now:
        data = connection.recv(1024)
        if not data:
            break
        else:
            data = data.decode("utf-8")
            print(f"{datetime.datetime.now()} - Received message: {data}")
            process_received_message(data)
            # Send sampling frequency to odometer
            new_frequency_message = {
                "new_odometer_frequency": odometer_gnss_frequency,
                "timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
                }
            connection.sendall(bytes(json.dumps(new_frequency_message), "utf-8"))

def upgrade_telemetry_publication_frequency(value):
    """Update telemetry publication frequency"""
    global telemetry_frequency
    telemetry_frequency = value
    print(f"Telemetry frequency updated to {telemetry_frequency} seconds")

def upgrade_sensors_sampling_frequency(value):
    """Update sensors sampling frequency"""
    global odometer_gnss_frequency
    odometer_gnss_frequency = value
    print(f"Sensors sampling frequency updated to {odometer_gnss_frequency} seconds")

def process_received_message(data):
    """
    Process incoming messages from sensors and update system state
    """
    global current_state, logs_telemetry, lock_telemetry, lock_current_state
    
    copy_current_state = {}

    with lock_current_state:
        data = json.loads(data)
        current_state["Timestamp"] = datetime.datetime.timestamp(datetime.datetime.now()) * 1000
        
        if data["Type"] == "GPS":
            current_state["Position"] = data["Position"]
            current_state["GPSSpeed"] = data["Speed"]
        elif data["Type"] == "Odometer":
            current_state["Speed"] = data["Speed"]
        elif data["Type"] == "CardReader":
            current_state["driver_present"] = data["driver_present"]

        copy_current_state = current_state.copy()
        print(f"Updated telemetry state: {json.dumps(copy_current_state, indent=4)}")
    
    with lock_telemetry:
        logs_telemetry.append(copy_current_state.copy())

def generate_event(event_type, description):
    """
    Generate and log a new event
    """
    global logs_event, lock_event, tachograph_id
    with lock_event:
        event = {
                "tachograph_id": tachograph_id,
                "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Position": current_state["Position"],
                "Event": event_type,
                "Description": description
            }

        print(f"EVENT: {json.dumps(event, indent=4)}")
        logs_event.append(event)

def data_logger():
    """
    Monitor system state and generate events based on conditions
    """
    global last_time, lock_current_state
    while not monitor.kill_now:
        with lock_current_state:
            if current_state["Timestamp"] > last_time:
                if current_state["driver_present"] == "None" and current_state["Speed"] > 0.0:
                    generate_event("Movement Without Driver", "Vehicle moving without driver.")
                if current_state["Speed"] > 90.0:
                    generate_event("Overspeed", "Speed above limit (90 km/h).")
                if abs(current_state["Speed"] - current_state["GPSSpeed"]) > (0.05 * current_state["Speed"]):
                    generate_event("Speed Discrepancy", "Difference > 5% between GPS and odometer.")
                last_time = current_state["Timestamp"]
        time.sleep(1)   

def on_connect(client, userdata, flags, rc):
    """
    MQTT connection callback
    Request access and subscribe to configuration topics
    """
    print(f"Connected with result code {rc}")
    if rc == 0:
        REQUEST_ACCESS_TOPIC = f"/fic/tachographs/{get_host_name()}/request_access/"
        request_access_message = {
            "tachograph_id": tachograph_id,
            "Timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
        }
        client.publish(REQUEST_ACCESS_TOPIC, payload=json.dumps(request_access_message), qos=1, retain=False)
        CONFIG_TOPIC = f"/fic/tachographs/{get_host_name()}/config/"
        client.subscribe(CONFIG_TOPIC)

        CONFIG_FREQUENCY_TOPIC = f"/fic/tachographs/{get_host_name()}/config_frequency/"
        client.subscribe(CONFIG_FREQUENCY_TOPIC)

def on_message(client, userdata, msg):
    """
    MQTT message callback
    Handle configuration and authorization messages
    """
    global connection_granted
    print(f"Received message: {msg.payload.decode()}")
    topic = msg.topic.split('/')
    json_config_received = json.loads(msg.payload.decode())
    
    if "config" in topic:
        if json_config_received["tachograph_id"] == tachograph_id and json_config_received["Authorization"] == "True":
            connection_granted = True
            print("Authorization True")
        else:
            print("Authorization False")
            connection_granted = False
            client.loop_stop()
            client.disconnect()
            os._exit(0)
    elif "config_frequency" in topic and connection_granted == True:
        if json_config_received["tachograph_id"] == tachograph_id and json_config_received["Config_item"] is not None:
            if json_config_received["Config_item"] == "telemetry_frequency":
                upgrade_telemetry_publication_frequency(json_config_received["Config_Value"])
            elif json_config_received["Config_item"] == "odometer_GNSS_frequency":
                upgrade_sensors_sampling_frequency(json_config_received["Config_Value"])

def mqtt_communications():
    """
    Handle MQTT communications
    Setup client, manage connection and publish data
    """
    global connection_granted
    client = mqtt.Client()
    client.username_pw_set(username="fic_server", password="fic_password")
    client.on_connect = on_connect
    client.on_message = on_message
    
    SESSION_TOPIC = f"/fic/tachographs/{get_host_name()}/session/"
    connection_dict = {
        "tachograph_id": tachograph_id,
        "Status": "Off - Unregulate Disconnection",
        "Timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
    }
    client.will_set(SESSION_TOPIC, json.dumps(connection_dict))
    
    MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS")
    MQTT_PORT = int(os.getenv("MQTT_SERVER_PORT"))
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    
    client.loop_start()

    while not monitor.kill_now:
        if connection_granted:
            publish_telemetry(client)
            publish_events(client)
            time.sleep(telemetry_frequency)
        else:
            time.sleep(10)
    
    if connection_granted:
        connection_dict = {
            "tachograph_id": tachograph_id,
            "Status": "Off - Regulate Disconnection",
            "Timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
        }
        info = client.publish(SESSION_TOPIC, payload=json.dumps(connection_dict), qos=1, retain=False)
        info.wait_for_publish()

    client.loop_stop()
    client.disconnect()
    print("MQTT client disconnected.")

def publish_telemetry(client):
    """Publish telemetry data to MQTT broker"""
    global logs_telemetry, lock_telemetry
    STATE_TOPIC = f"/fic/tachographs/{get_host_name()}/telemetry/"
    number_telemetries_sent = 0
    with lock_telemetry:
        while number_telemetries_sent < len(logs_telemetry):
            client.publish(STATE_TOPIC, payload=json.dumps(logs_telemetry[number_telemetries_sent]), qos=1, retain=False)
            number_telemetries_sent += 1
        logs_telemetry = []

def publish_events(client):
    """Publish events to MQTT broker"""
    global logs_event, lock_event
    STATE_TOPIC = f"/fic/tachographs/{get_host_name()}/event/"
    number_events_sent = 0
    with lock_event: 
        while number_events_sent < len(logs_event):
            client.publish(STATE_TOPIC, payload=json.dumps(logs_event[number_events_sent]), qos=1, retain=False)
            number_events_sent += 1
        logs_event = []

if __name__ == '__main__':
    try:
        # Start MQTT communications thread
        t1 = threading.Thread(target=mqtt_communications, daemon=True)
        t1.start()

        # Start data logger thread
        t2 = threading.Thread(target=data_logger, daemon=True)
        t2.start()
        
        # Setup TCP server
        HOST = get_host_name()
        PORT = int(os.getenv("UC_SIMULATOR_PORT"))

        # Get tachograph component names
        ODOMETER_SIMULATOR_HOST = os.getenv("ODOMETER_SIMULATOR_HOST")
        GNSS_SIMULATOR_HOST = os.getenv("GNSS_SIMULATOR_HOST")
        CARD_READER_HOST = os.getenv("CARD_READER_HOST")

        # Listen for connections from components
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen(3)
            
            while not monitor.kill_now:
                print(f"{datetime.datetime.now()} - Waiting for connection...")
                connection, address = s.accept()

                # Get connecting component's hostname
                hostname = socket.gethostbyaddr(address[0])
                print("Machine name:", hostname[0])

                # Start appropriate handler thread based on component type
                if ODOMETER_SIMULATOR_HOST in hostname[0].split("."):
                    print("Odometer connection")
                    threading.Thread(target=client_listener_odometer, args=(connection, address)).start()
                elif GNSS_SIMULATOR_HOST in hostname[0].split("."):
                    print("GNSS connection")
                    threading.Thread(target=client_listener_positioning_system, args=(connection, address)).start()
                elif CARD_READER_HOST in hostname[0].split("."):
                    print("Card reader connection")
                    threading.Thread(target=client_listener_card_reader, args=(connection, address)).start()
        
        t1.join()
        t2.join()
    except Exception as e:
        print(f"Fatal error: {e}")

