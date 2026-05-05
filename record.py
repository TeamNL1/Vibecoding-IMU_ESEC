import csv
import socket
import time
from datetime import datetime

from config import CSV_FILE, UDP_IP, UDP_PORT, USB_BAUDRATE, USB_PORT
from ximu_parser import parse_packet


def select_usb_port(usb_port_override=None):
    if usb_port_override:
        return usb_port_override
    if USB_PORT:
        return USB_PORT

    try:
        from serial.tools import list_ports
        import serial
    except ImportError:
        print("pyserial ontbreekt. Installeer met: pip install pyserial")
        return None

    ports = list(list_ports.comports())
    if not ports:
        print("Geen COM-poorten gevonden.")
        return None

    print("Beschikbare COM-poorten:")
    for index, port in enumerate(ports, start=1):
        desc = port.description or "Onbekend apparaat"
        print(f"  {index}. {port.device} ({desc})")

    while True:
        choice = input("Kies COM-poortnummer: ").strip()
        try:
            idx = int(choice)
        except ValueError:
            print("Voer een geldig nummer in.")
            continue

        if 1 <= idx <= len(ports):
            selected = ports[idx - 1].device
            try:
                probe = serial.Serial(selected, baudrate=USB_BAUDRATE, timeout=0.2)
                probe.close()
                return selected
            except FileNotFoundError as exc:
                print(f"Die poort is niet direct openbaar: {exc}")
                print("Probeer de sensor los te koppelen en opnieuw aan te sluiten, of kies een andere poort.")
                return None
            except Exception as exc:
                print(f"Die poort kan nu niet geopend worden: {exc}")
                print("Probeer de sensor los te koppelen en opnieuw aan te sluiten, of kies een andere poort.")
                return None

        print("Nummer buiten bereik.")


def _write_header(writer):
    writer.writerow(["pc_time", "sensor_time", "gx", "gy", "gz", "ax", "ay", "az"])


def _handle_packet(data, source, writer, debug=True):
    if debug:
        print(f"\n--- RAW DATA VAN {source} ---")
        print(data)
        try:
            print("ALS TEKST:", data.decode("utf-8", errors="replace").strip())
        except Exception:
            pass

    parsed = parse_packet(data)

    if not parsed:
        if debug:
            print("NIET HERKEND DOOR PARSER")
        return False

    sensor_time, gx, gy, gz, ax, ay, az = parsed

    writer.writerow([
        datetime.now().isoformat(),
        sensor_time,
        gx,
        gy,
        gz,
        ax,
        ay,
        az,
    ])

    if debug:
        print("PARSED:", parsed)
        print("OPGESLAGEN IN CSV")

    return True


def record_udp(duration_seconds=30, output_file=CSV_FILE, debug=True):
    print(f"UDP config: IP={UDP_IP}, PORT={UDP_PORT}")
    print("Let op: UDP_IP moet meestal 0.0.0.0 zijn.")
    print("In de x-IMU3 moet Send Port gelijk zijn aan deze poort.\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.bind((UDP_IP, UDP_PORT))
    except OSError as exc:
        print(f"Kan niet luisteren op UDP {UDP_IP}:{UDP_PORT}")
        print(exc)
        print("\nMogelijke oorzaak:")
        print("- Er draait nog een ander script op dezelfde poort.")
        print("- Sluit oude VS Code debug sessies.")
        print(f"- Check met: netstat -ano | findstr :{UDP_PORT}")
        return

    sock.settimeout(1.0)

    print(f"Luisteren op UDP {UDP_IP}:{UDP_PORT}...")
    print(f"Recording voor {duration_seconds} seconden...")
    print("Wachten op data...\n")

    start_time = time.time()
    received_any = False
    saved_rows = 0

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        _write_header(writer)

        try:
            while time.time() - start_time < duration_seconds:
                try:
                    data, addr = sock.recvfrom(4096)
                except socket.timeout:
                    continue

                received_any = True
                if _handle_packet(data, f"UDP {addr}", writer, debug=debug):
                    saved_rows += 1

        except KeyboardInterrupt:
            print("\nHandmatig gestopt.")
        finally:
            sock.close()

    print("\n--- RESULTAAT UDP RECORDING ---")
    print(f"Data ontvangen: {'ja' if received_any else 'nee'}")
    print(f"CSV-rijen opgeslagen: {saved_rows}")
    print(f"Bestand: {output_file}")


def record_usb(duration_seconds=30, output_file=CSV_FILE, usb_port=None, debug=True):
    try:
        import serial
    except ImportError:
        print("pyserial ontbreekt. Installeer met: pip install pyserial")
        return

    selected_port = select_usb_port(usb_port)

    if not selected_port:
        print("Geen USB-poort gekozen.")
        return

    print(f"Verbinden met USB {selected_port} @ {USB_BAUDRATE} baud...")

    try:
        ser = serial.Serial(selected_port, baudrate=USB_BAUDRATE, timeout=1.0)
    except FileNotFoundError as exc:
        print(f"Kan USB-poort {selected_port} niet openen: {exc}")
        print("Mogelijke oorzaken:")
        print("- De sensor is net losgekoppeld of opnieuw verbonden.")
        print("- De gekozen COM-poort hoort niet bij de x-IMU3.")
        print("- Een ander programma houdt de poort bezet.")
        return
    except Exception as exc:
        print(f"Kan USB-poort niet openen: {exc}")
        return

    print(f"Recording voor {duration_seconds} seconden...")
    print("Wachten op data...\n")

    start_time = time.time()
    received_any = False
    saved_rows = 0
    buffer = bytearray()

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        _write_header(writer)

        try:
            while time.time() - start_time < duration_seconds:
                chunk = ser.read(ser.in_waiting or 1)
                if not chunk:
                    continue

                buffer.extend(chunk)

                while True:
                    newline_index = buffer.find(b"\n")
                    if newline_index < 0:
                        break

                    data = bytes(buffer[: newline_index + 1])
                    del buffer[: newline_index + 1]

                    received_any = True
                    if _handle_packet(data, f"USB {selected_port}", writer, debug=debug):
                        saved_rows += 1

        except KeyboardInterrupt:
            print("\nHandmatig gestopt.")
        finally:
            ser.close()

    print("\n--- RESULTAAT USB RECORDING ---")
    print(f"Data ontvangen: {'ja' if received_any else 'nee'}")
    print(f"CSV-rijen opgeslagen: {saved_rows}")
    print(f"Bestand: {output_file}")


def record_data(duration_seconds=30, output_file=CSV_FILE, transport="udp", usb_port=None, debug=True):
    transport = transport.lower().strip()

    if transport == "udp":
        record_udp(duration_seconds=duration_seconds, output_file=output_file, debug=debug)
    elif transport == "usb":
        record_usb(duration_seconds=duration_seconds, output_file=output_file, usb_port=usb_port, debug=debug)
    else:
        raise ValueError("transport moet 'udp' of 'usb' zijn")
