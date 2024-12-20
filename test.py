import serial
import serial.tools.list_ports
import re

# Function to list all COM ports and their MAC addresses
def list_com_ports_with_mac():
    ports = serial.tools.list_ports.comports()
    mac_pattern = re.compile(r'([0-9A-F]{12})', re.I)
    for port in ports:
        mac_address = mac_pattern.search(port.hwid)
        if mac_address:
            formatted_mac = ':'.join(mac_address.group(0)[i:i+2] for i in range(0, 12, 2))
            print(f"Port: {port.device}, Description: {port.description}, MAC Address: {formatted_mac}")
        else:
            print(f"Port: {port.device}, Description: {port.description}, MAC Address: Not found")

# Function to find the COM port of the Bluetooth device by MAC address
def find_bluetooth_port_by_mac(mac_address):
    ports = serial.tools.list_ports.comports()
    mac_pattern = re.compile(r'([0-9A-F]{12})', re.I)
    for port in ports:
        found_mac = mac_pattern.search(port.hwid)
        if found_mac and mac_address.lower() == ':'.join(found_mac.group(0)[i:i+2] for i in range(0, 12, 2)).lower():
            return port.device
    return None

# List all available COM ports and their MAC addresses
list_com_ports_with_mac()

# Replace with your Bluetooth device's MAC address
bluetooth_mac_address = "00:80:5F:9B:34:FB"

# Find the COM port for the Bluetooth device with the given MAC address
com_port = find_bluetooth_port_by_mac(bluetooth_mac_address)

if com_port:
    print(f"Found device with MAC address {bluetooth_mac_address} on {com_port}")
    # Configure the serial port
    ser = serial.Serial(
        port=com_port,
        baudrate=9600,
        timeout=1
    )
else:
    print(f"Device with MAC address {bluetooth_mac_address} not found")