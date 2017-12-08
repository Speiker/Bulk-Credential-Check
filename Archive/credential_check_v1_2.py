#########################################################################
# Use: Check credentials against multiple devices and log connections   #
# Version: 1.2                                                          #
#                                                                       #
# Input: devices.txt file with one device hostname or IP address per    #
#        line. This can include CIDR networks                           #
# Output: Info is output to screen and logged (username_checked.csv).   #
#         Offers to export available devices found to file.             #
#                                                                       #
# Assumptions: Telnet connections should be formatted as follows        #
#                 Username:                                             #
#                 Password:                                             #
#                 Hostname# or Hostname>                                #
#              Script keys off "Username:", "Password:", and "#" or ">" #
#              to validate successful connections                       #
#########################################################################

# Used to colorize output
from colorama import init
from colorama import Fore
# Used to get user credentials and mask user input for passwords
import getpass
# Used for SSH connections
from netmiko import ConnectHandler
# Used for telnet connections
import telnetlib
# Used for file naming purposes
from time import strftime
# Used to verify device availability
import os
# Used to check OS type
from sys import platform
# Used to convert CIDR to hosts
from netaddr import IPNetwork

# colorama initialization, required for windows
init(autoreset=True)


# Display script name and version
user_message = Fore.YELLOW + "Credential Check - v1.2\n\n" + Fore.WHITE
print(user_message)


def main():
    initialize_script()
    # Run initial connection test
    connection_test()
    # Offer to run additional connection tests
    additional_test()


def initialize_script():
    # Prompt for user credentials
    global username, password, enablepw
    username, password, enablepw = user_credentials()
    device_export = 'n'

    # Offer to check availability of devices before scanning
    user_message = Fore.CYAN + "\nWould you like to check availability before scanning? (y/n) " + Fore.WHITE
    avail_check = input(user_message)
    if avail_check.lower() == 'y':
        # Offer to save available devices found to file
        user_message = Fore.CYAN + "\nWould you like to export available devices found to file? (y/n) " + Fore.WHITE
        device_export = input(user_message)
        if device_export.lower() == 'y':
            user_message = Fore.CYAN + "    Please enter name for the file: " + Fore.WHITE
            device_file = input(user_message)

            if device_file.endswith('.txt'):
                device_file = device_file.strip()
            else:
                device_file = device_file.strip() + '.txt'

    # Initialize variables needed for devices
    global device_list
    global device
    # Create device list to populate from devices.txt
    device_list = []
    
    # open the devices text file in read-only mode
    if avail_check == 'y':
        print(Fore.MAGENTA + "\n\nImporting devices and checking availability..." + Fore.WHITE)
    else:
        print(Fore.MAGENTA + "\n\nImporting devices..." + Fore.WHITE)
    with open('devices.txt', 'r') as fn:

        # iterate through the lines in the text file
        for line in fn.read().splitlines():

            # skip empty lines
            if line is '':
                continue

            else:
                if avail_check == 'y':
                    print(Fore.MAGENTA + "    Checking " + str(line) + Fore.WHITE)
                # Check if CIDR network was entered
                if "/" in line:
                    # Convert CIDR to individual hosts
                    for ip in IPNetwork(line):
                        # Converted host from CIDR is device
                        device = ip
                        if avail_check == 'y':
                            # Function to check availability if requested
                            online_device_add()
                        else:
                            device_list.append(str(device))
                else:
                    # entire line is device
                    device = line
                    if avail_check == 'y':
                        # Function to check availability if requested
                        online_device_add()
                    else:
                        device_list.append(str(device))


    # Write available devices to file if requested earlier
    if device_export.lower() == 'y':
        device_log = open(device_file, 'w')
        for device in device_list:
            device_log.write(device + "\n")
        device_log.close()


def user_credentials():
    # Get user credentials to test
    print(Fore.CYAN + "Please enter credentials to check." + Fore.WHITE)
    username = input("\nUsername: ")
    password = getpass.getpass("Password: ")
    enablepw = password

    return username, password, enablepw


def online_device_add():
    # Function to check if device is online

    # Checks host OS type and pings remote devices to determine availability
    if "linux" in platform:
        response = os.system("ping -c 1 -w 2 " + str(device) + " > /dev/null 2>&1")
    elif "win" in platform:
        response = os.system("ping -c 1 " + str(device) + " /f >nul 2>&1")

    # Add device to device list if reachable
    if response == 0:
        device_list.append(str(device))


def connection_test():
    print(Fore.MAGENTA + "\n\nTesting access to devices for " + str(username) + "." + Fore.WHITE)
    
    # Set log file name to match username tested and initialize log
    logname = username + "_" + strftime("%Y-%m-%d_%H%M") +".csv"
    file = open(logname, 'w')
    # Add header information
    file.write("device,authentication type\n")

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
                tn.read_until(b"Username: ",2)
                tn.write(username.encode('ascii') + b"\n")
                # Listen for password prompt and send password
                tn.read_until(b"Password: ",2)
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
                user_message = Fore.MAGENTA + "   " + str(device) + " accessible via " + str(auth_type) + "!" + Fore.WHITE
        print(user_message)
        
    # close log
    file.close()


def additional_test():
    # Offer to test another set of credentials
    user_message = Fore.CYAN + "\nWould you like to check additional credentials? (y/n) " + Fore.WHITE
    additional_prompt = input(user_message)
    
    if additional_prompt.lower() == 'y':
        # Prompt for user credentials
        global username, password, enablepw
        username, password, enablepw = user_credentials()
    
        # Run additional tests
        connection_test()
        additional_test()


main()
