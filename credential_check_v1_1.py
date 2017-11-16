#########################################################################
# Use: Check credentials against multiple devices and log connections   #
# Version: 1.1                                                          #
#                                                                       #
# Input: devices.txt file with one device hostname or IP address per    #
#        line. This can include CIDR networks                           #
# Output: Info is output to screen and logged (username_checked.csv).   #
#                                                                       #
# Assumptions: Telnet connections should be formatted as follows        #
#                 Username:                                             #
#                 Password:                                             #
#                 Hostname# or Hostname>                                #
#              Script keys off "Username:", "Password:", and "#" or ">" #
#              to validate successful connections                       #
#########################################################################

# Import colorama to colorize output
from colorama import init
from colorama import Fore
# Import getpass so we can easily mask user input for passwords
import getpass
# Import ConnectHandler for SSH connections
from netmiko import ConnectHandler
# Import telnetlib for telnet connections
import telnetlib
# Import strftime for file naming purposes and run-time
from time import strftime
# Used for run time calculations
from datetime import datetime
# Used to check if devices are online to check
import os
# Used to convert CIDR to hosts
from netaddr import IPNetwork
# Used to scan ports
import socket
import subprocess

# colorama initialization, required for windows
init(autoreset=True)


# Display script name and version
user_message = Fore.YELLOW + "Credential Check - v1.1\n\n" + Fore.WHITE
print(user_message)


# Get user credentials to test
print(Fore.CYAN + "Please enter credentials to check." + Fore.WHITE)
username = input("\nUsername: ")
password = getpass.getpass("Password: ")
enablepw = password


# Setting a start time for script
t1 = datetime.now()


# Create device list to populate from devices.txt
device_list = []

def online_device_add():
    # Function to check if device has open ports before adding to device list

    # Variable initialization
    available = False

    # Set ports to scan (SSH and Telnet)
    ports = [22,23]

    # Scan for open ports an mark as available if they are
    try:
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((device, port))
            if result == 0:
                available = True
            sock.close()
    except socket.error:
        sys.exit()
    except KeyboardInterrupt:
        print ("\n\nYou pressed Ctrl+C for " + device)
        sys.exit()

    # Add device to device list if reachable
    if available:
        device_list.append(str(device))


# open the devices text file in read-only mode
print(Fore.MAGENTA + "\n\nImporting devices and checking availability..." + Fore.WHITE)
with open('devices.txt', 'r') as fn:

    # iterate through the lines in the text file
    for line in fn.read().splitlines():

        # skip empty lines
        if line is '':
            continue

        else:
            print(Fore.MAGENTA + "    Checking " + str(line) + Fore.WHITE)
            # Check if CIDR network was entered
            if "/" in line:
                # Convert CIDR to individual hosts
                for ip in IPNetwork(line):
                    # Converted host from CIDR is device
                    device = str(ip)
                    # Function to check reachability
                    online_device_add()
            else:
                # entire line is device
                device = line
                # Function to check reachability
                online_device_add()


# Set log file name to match username tested and initialize log
logname = username + "_" + strftime("%Y-%m-%d_%H%M") +".csv"
file = open(logname, 'w')
# Add header information
file.write("device,authentication type\n")


print(Fore.MAGENTA + "\n\nTesting connections to online devices..." + Fore.WHITE)
# This loop will test SSH then Telnet connections to every device in the list
for device in device_list:

    auth_type = ""

    # Create a heading so if there are multiple devices, you know what the output is for
    print ("\n----------------------\n" + str(device) + "\n----------------------\n")

    # Use a try, so it doesn't throw an exception and cancel out of the script.
    try:
        # We need to set the various options Netmiko is expecting. 
        # We use the variables we got from the user earlier
        network_device_param = {
            'device_type': 'cisco_ios_ssh',
            'ip': device,
            'username': username,
            'password': password,
            'secret': enablepw,
        }
        # This command is when we are attempting to connect. If it fails, it will move on to the except block below
        net_connect = ConnectHandler(**network_device_param)
        # This variable will be used to report successful connections
        auth_type = "SSH"
        # Close session
        net_connect.disconnect()
    except:
        try:
            # Here we are saying "if ssh failed, TRY telnet"
            # Use telnetlib to attempt to connect
            tn = telnetlib.Telnet(device)
            # Listen for username prompt and send username
            tn.read_until(b"Username: ")
            tn.write(username.encode('ascii') + b"\n")
            # Listen for password prompt and send password
            tn.read_until(b"Password: ")
            tn.write(password.encode('ascii') + b"\n")
            # Check output to verify successful connection
            conn_output = tn.read_until(b"#",2)
            if b"#" in conn_output:
                # This variable will be used to report successful connections
                auth_type = "Telnet"
            elif b">" in conn_output:
                # This variable will be used to report successful connections
                auth_type = "Telnet"
            else:
                auth_type = "Credentials incorrect but Telnet open"
                user_message = Fore.MAGENTA + "   Credentials incorrect, but Telnet open." + Fore.WHITE
            # Close Telnet sesstion
            tn.close
        except:
            # This is the catch all except, if NOTHING works, tell the 
            # user and continue onto the next item in the for loop.
            user_message = Fore.MAGENTA + "   Unable to connect." + Fore.WHITE

    # Add connection attempts to log
    file.write(device + "," + auth_type + "\n")

    # Prints connection results to screen
    if auth_type != "":
        if auth_type != "Credentials incorrect but Telnet open":
            user_message = Fore.MAGENTA + "   " + str(device) + " vulnerable using " + str(auth_type) + "!" + Fore.WHITE
    print(user_message)


# close log
file.close()

# Setting a finish time for script
t2 = datetime.now()

# Calculates the difference of time, to see how long it took to run the script
total =  t2 - t1

# Printing the information to screen
print ('\n\nScanning Completed in: ' + str(total))
