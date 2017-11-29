# Bulk-Credential-Check

This script was written to check a set of credentials against multiple devices and log the results. 

Input: devices.txt file with one device hostname or IP address per line. IP addresses can be formatted as CIDR networks. The script will break them out into individual devices to be scanned.

Output: Results are output to screen and logged ('username_checked.csv').

Assumptions: Telnet connections are scripted to be recognized as follows:

     Username:
     Password:
     Hostname# or Hostname>

This script keys off "Username: ", "Password: ", and "#" or ">" to validate successful telnet connections. If any of those are not found within 2 seconds of reading output the authentication attempt will timeout.


v1.0 - Pings imported devices to determine availability then attempts to connect.

v1.1 - Scans ports 22 and 23 of imported devices to determine availability then attempts to connect.

v1.2 - Changed back to ping for availablity check. Made device availability check optional as well as added an option to export the device list to a file after availability was checked and test additional credentials after initial scan. Converted much of the script into  various functions.

v1.3 - Added threading to support multiple simultaneous connections. Set max concurrent connections to 50. SSH config file (sshd_config) will need to be modified in order to support that many outbound connections (MaxSessions and MaxStartups fields).
