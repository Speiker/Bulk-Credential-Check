# Bulk-Credential-Check

This script was written to check a set of credentials against multiple devices and log the results. 

Input: devices.txt file with one device hostname or IP address per line. IP addresses can be formatted as CIDR networks. The script will break them out into individual devices to be scanned.
Output: Results are output to screen and logged ('username_checked.csv').

Assumptions: Telnet connections are scripted to be recognized as follows:
              Username:
              Password:
              Hostname# or Hostname>
            This script keys off "Username: ", "Password: ", and "#" or ">" to validate successful connections.
