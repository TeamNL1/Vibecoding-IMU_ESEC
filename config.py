"""
Centrale instellingen voor x-IMU3 project.

Pas vooral UDP_PORT aan als je in de x-IMU3 software ook een andere
Send Port hebt ingesteld.
"""

# UDP / Wi-Fi
UDP_IP = "0.0.0.0"      # Luister op alle netwerkkaarten van deze laptop
UDP_PORT = 9000         # Moet gelijk zijn aan Send Port in x-IMU3

# USB / COM
USB_PORT = None         # None = laat script COM-poort kiezen
USB_BAUDRATE = 115200

# Data
CSV_FILE = "ximu3_data.csv"
RECORD_SECONDS = 30
