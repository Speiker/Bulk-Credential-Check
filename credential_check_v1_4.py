#########################################################################
# Use: Check credentials against multiple devices and log connections   #
# Version: 1.4                                                          #
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
# Used to report scan time
from datetime import datetime
# Used to verify device availability
import os
# Used to check OS type
from sys import platform
# Used to convert CIDR to hosts
from netaddr import IPNetwork
# Used to support multiple connections
import threading

# colorama initialization, required for windows
init(autoreset=True)


# Display script name and version
user_message = Fore.YELLOW + "\n\nCredential Check - v1.4\n\n" + Fore.WHITE
print(user_message)


# Limits the number of simultaneous threads and screen writes
maxthreads = 50
sema = threading.BoundedSemaphore(value=maxthreads)
screenlock = threading.Semaphore(value=1)

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
    temp_list = []
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
                    print(Fore.MAGENTA + "    Adding " + str(line) + Fore.WHITE)
                # Check if CIDR network was entered
                if "/" in line:
                    # Convert CIDR to individual hosts
                    for ip in IPNetwork(line):
                        # Converted host from CIDR is device
                        device = ip
                        temp_list.append(str(device))
                else:
                    # entire line is device
                    device = line
                    temp_list.append(str(device))


    # Check availability of devices if requested
    if avail_check == 'y':
        threads = []
        print(Fore.MAGENTA + "\n    Checking availability..." + Fore.WHITE)
        for device in temp_list:
            my_thread = threading.Thread(target=online_device_add, args=(device,))
            # Pull from pool of available threads
            sema.acquire()
            # Start thread
            my_thread.start()
            threads.append(my_thread)

        # Joining will ensure all threads complete before continuing
        main_thread = threading.currentThread()
        for t in threads:
            if t != main_thread:
                t.join()
    else:
        device_list = temp_list


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


def online_device_add(device):
    # Function to check if device is online

    # Pull from pool of available threads
    #sema.acquire()

    # Checks host OS type and pings remote devices to determine availability
    if "linux" in platform:
        response = os.system("ping -c 1 -w 2 " + str(device) + " > /dev/null 2>&1")
    elif "win" in platform:
        response = os.system("ping -c 1 " + str(device) + " /f >nul 2>&1")

    # Add device to device list if reachable
    if response == 0:
        device_list.append(str(device))

    # Release thread to pool
    sema.release()


def test(device,device_count):
    auth_type = ""

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
            tn = telnetlib.Telnet(device,23,2)
            # Listen for username prompt and send username
            tn.read_until(b"Username: ",2)
            tn.write(username.encode('ascii') + b"\n")
            # Listen for password prompt and send password
            tn.read_until(b"Password: ",2)
            tn.write(password.encode('ascii') + b"\n")
            # Check output to verify successful connection
            conn_output = tn.read_until(b"#",2)
            if b"password>" in conn_output:
                # Arris modem password prompt
                # Send password
                tn.write(password.encode('ascii') + b"\n")
                # Check output to verify successful connection
                arris_output = tn.read_until(b"Console>",2)
                if b"Console>" in arris_output:
                    # This variable will be used to report successful connections
                    auth_type = "Telnet"
                else:
                    auth_type = "Credentials incorrect but Telnet open"
                    user_message = Fore.MAGENTA + "   Credentials incorrect, but Telnet open." + Fore.WHITE
            elif b"#" in conn_output:
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

    # Lock output to this thread
    screenlock.acquire()

    # Add connection result to log
    file = open(logname, 'a')
    file.write(device + "," + auth_type + "\n")
    file.close()

    # Prints connection result to screen
    # Create a heading so if there are multiple devices, you know what the output is for
    print ("\n----------------------------\n" + 
        str(device) + " - " + 
        str(threading.active_count()) + 
        " threads\n----------------------------\n"
    )

    if auth_type != "":
        if auth_type != "Credentials incorrect but Telnet open":
            user_message = Fore.MAGENTA + "   " + str(device) + " accessible via " + str(auth_type) + "!" + Fore.WHITE
    print(user_message)

    # Release screenlock
    screenlock.release()
    # Release thread to pool
    sema.release()


def connection_test():
    print(Fore.MAGENTA + "\n\nTesting access to devices for " + str(username) + "." + Fore.WHITE)

    # Record start time of scan
    start_time = datetime.now()
    # Set log file name to match username tested and initialize log
    global file
    global logname
    logname = username + "_" + strftime("%Y-%m-%d_%H%M") +".csv"
    file = open(logname, 'w')
    # Add header information
    file.write("device,authentication type\n")
    # Close log after writing header; additional logs will be appended
    file.close()

    # This loop will test SSH then Telnet connections to every device in the list
    threads = []
    for device in device_list:
        device_count = device_list.index(device)
        my_thread = threading.Thread(target=test, args=(device,device_count,))
        # Pull from pool of available threads
        sema.acquire()
        # Start thread
        my_thread.start()
        threads.append(my_thread)

    # Joining will ensure all threads complete before continuing
    main_thread = threading.currentThread()
    for t in threads:
        if t != main_thread:
            t.join()

    # Prints scanning details
    print(Fore.CYAN + "\nTotal devices scanned: " + str(len(device_list)) + Fore.WHITE)
    print(Fore.CYAN + "   Elapsed time: " + str(datetime.now() - start_time) + Fore.WHITE)

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


if __name__ == "__main__":
    main()
