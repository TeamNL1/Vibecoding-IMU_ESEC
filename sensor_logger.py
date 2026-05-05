import csv
import json
import shutil
import string
import time
from dataclasses import dataclass
from pathlib import Path

from config import USB_BAUDRATE
from ximu_parser import parse_packet


DOWNLOAD_DIR = Path("downloads")
SESSION_STATE_FILE = Path(".ximu3_session.json")


@dataclass(frozen=True)
class SensorItem:
    label: str
    source: Path
    kind: str


def _format_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0


def _unique_path(path):
    if not path.exists():
        return path

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _session_state_path():
    return Path.cwd() / SESSION_STATE_FILE


def _save_session_state(prefix):
    state = {
        "prefix": prefix,
    }
    try:
        _session_state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"Kan sessiestatus niet opslaan: {exc}")


def _load_session_state():
    path = _session_state_path()
    try:
        if not path.is_file():
            return None
        state = json.loads(path.read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _clear_session_state():
    path = _session_state_path()
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _sanitize_prefix(prefix):
    cleaned = []
    for char in prefix.strip():
        if char.isalnum() or char in {"-", "_", "."}:
            cleaned.append(char)
        elif char.isspace():
            cleaned.append("-")
    result = "".join(cleaned).strip("-_.")
    return result or "Session"


def _read_command_ack(conn, expected_key, timeout=3.0):
    deadline = time.time() + timeout
    buffer = bytearray()
    expected = expected_key.lower()
    last_text = None

    while time.time() < deadline:
        chunk = conn.read(conn.in_waiting or 1)
        if chunk:
            buffer.extend(chunk)

        while True:
            newline_index = buffer.find(b"\n")
            if newline_index < 0:
                break

            line = bytes(buffer[:newline_index]).strip()
            del buffer[: newline_index + 1]

            if not line:
                continue

            text = line.decode("utf-8", errors="replace").strip()
            last_text = text

            if not text.startswith("{"):
                continue

            try:
                message = json.loads(text)
            except json.JSONDecodeError:
                continue

            if isinstance(message, dict) and any(key.lower() == expected for key in message):
                return True, message

    return False, last_text


def _send_usb_command_and_get_response(usb_port, payload, expected_key):
    message = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")

    try:
        import serial
    except ImportError:
        print("pyserial ontbreekt. Installeer met: pip install pyserial")
        return False

    try:
        with serial.Serial(usb_port, baudrate=USB_BAUDRATE, timeout=1.0, write_timeout=1.0) as conn:
            conn.reset_input_buffer()
            conn.write(message)
            conn.flush()

            ok, response = _read_command_ack(conn, expected_key)
            if ok:
                return response

        if response:
            print(f"Onverwachte USB-response: {response}")
            print("Het commando werd niet beantwoord met de verwachte JSON-ack.")
        else:
            print("Geen USB-ack ontvangen.")
        return None
    except Exception as exc:
        print(f"Kan USB-command niet sturen: {exc}")
        print("Controleer of de sensor echt als COM-poort zichtbaar is en niet door een ander programma gebruikt wordt.")
        return None


def _send_usb_command(usb_port, payload, expected_key):
    response = _send_usb_command_and_get_response(usb_port, payload, expected_key)
    if response is not None:
        print(f"USB ACK: {response}")
        return True
    return False


def _read_setting(usb_port, setting_key):
    response = _send_usb_command_and_get_response(usb_port, {setting_key: None}, setting_key)
    if not isinstance(response, dict):
        return None

    return response.get(setting_key)


def _list_usb_ports():
    try:
        from serial.tools import list_ports
    except ImportError:
        print("pyserial ontbreekt. Installeer met: pip install pyserial")
        return []

    return list(list_ports.comports())


def _choose_usb_port_from_ports(ports):
    if not ports:
        return None

    if len(ports) == 1:
        return ports[0].device

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
            return ports[idx - 1].device

        print("Nummer buiten bereik.")


def start_sensor_logging():
    print("\n=== OPTIE 3: opname op sensor starten ===")

    ports = _list_usb_ports()
    usb_port = _choose_usb_port_from_ports(ports)
    if not usb_port:
        print("Geen USB COM-poort gekozen.")
        return

    prefix = input("Bestandsnaam-prefix voor de opname [Session]: ").strip()
    prefix = _sanitize_prefix(prefix or "Session")

    auto_enabled = _read_setting(usb_port, "data logger automatic start stop enabled")

    if auto_enabled is True:
        print("Controle: automatic start stop = AAN")
    elif auto_enabled is False:
        print("Controle: automatic start stop = UIT")
    else:
        print("Controle: automatic start stop kon niet worden uitgelezen")

    if auto_enabled is True:
        print("Automatic start stop staat aan. Ik zet eerst de bestandsnaam-prefix en herstart daarna de sensor.")

        if not _send_usb_command(usb_port, {"data logger file name prefix": prefix}, "data logger file name prefix"):
            print("Prefix kon niet worden ingesteld.")
            return

        if not _send_usb_command(usb_port, {"apply": None}, "apply"):
            print("Instellingen konden niet direct worden toegepast.")
            return

        print(f"Prefix ingesteld op '{prefix}'.")
        print("Ik stuur nu een reset zodat de sensor opnieuw opstart en automatisch een nieuw logbestand begint.")
        if _send_usb_command(usb_port, {"reset": None}, "reset"):
            print("Reset verstuurd.")
            _save_session_state(prefix=prefix)
            print("Wacht even tot de sensor opnieuw is opgestart. Daarna zou een nieuw bestand moeten worden aangemaakt.")
            print("Je kunt de sensor nu loskoppelen en later opnieuw verbinden om het bestand te zien.")
        else:
            print("Reset-command is mislukt.")
        return

    print("Automatic start stop staat niet aan, dus ik gebruik het start-commando direct.")
    print(f"Start opname op sensor met prefix '{prefix}'...")
    if _send_usb_command(usb_port, {"start": prefix}, "start"):
        print("Opname gestart.")
        _save_session_state(prefix=prefix)
        print("Je kunt de sensor nu loskoppelen terwijl hij logt.")
    else:
        print("Start-command is mislukt.")


def stop_sensor_logging():
    print("\n=== OPTIE 4: opname op sensor stoppen ===")

    ports = _list_usb_ports()
    usb_port = _choose_usb_port_from_ports(ports)
    if not usb_port:
        print("Geen USB COM-poort gekozen.")
        return

    print("Stop opname op sensor...")
    if _send_usb_command(usb_port, {"stop": None}, "stop"):
        print("Opname gestopt.")
        session = _load_session_state() or {}
        if download_latest_sensor_file_to_workdir(
            prefix=session.get("prefix"),
        ):
            _clear_session_state()
            print("Laatste bestand is toegevoegd aan de werkmap.")
        else:
            print("Er kon geen bestand uit de sensor worden toegevoegd.")
    else:
        print("Stop-command is mislukt.")


def _drive_roots():
    for letter in string.ascii_uppercase:
        root = Path(f"{letter}:/")
        try:
            if root.exists():
                yield root
        except OSError:
            continue


def find_ximu3_drive():
    for root in _drive_roots():
        try:
            if (root / "Data Logger").is_dir() or (root / "Calibration Certificate.html").is_file():
                return root
        except OSError:
            continue
    return None


def _collect_downloadable_items(drive_root):
    items = []

    cert = drive_root / "Calibration Certificate.html"
    try:
        if cert.is_file():
            items.append(SensorItem("Calibration Certificate.html", cert, "cert"))
    except OSError:
        pass

    data_logger = drive_root / "Data Logger"
    try:
        if data_logger.is_dir():
            files = [path for path in data_logger.glob("*.ximu3") if path.is_file()]
            files.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
            for path in files:
                items.append(SensorItem(f"Data Logger/{path.name}", path, "log"))
    except OSError:
        pass

    return items


def _print_items(items):
    print("\nBeschikbare bestanden op de sensor:")
    for index, item in enumerate(items, start=1):
        try:
            size = _format_size(item.source.stat().st_size)
        except OSError:
            size = "onbekend"
        print(f"  {index}. [{item.kind.upper()}] {item.label} ({size})")


def _convert_ximu3_to_csv(source_path, csv_path):
    rows = 0

    try:
        with source_path.open("rb") as source_file, csv_path.open("w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["sensor_time", "gx", "gy", "gz", "ax", "ay", "az"])

            for raw_line in source_file:
                parsed = parse_packet(raw_line)
                if parsed:
                    writer.writerow(parsed)
                    rows += 1
    except Exception as exc:
        print(f"CSV-conversie mislukt voor {source_path.name}: {exc}")
        return None

    if rows == 0:
        print(f"Geen parsebare data gevonden in {source_path.name}.")
        return None

    return csv_path


def _latest_log_item(drive_root, prefix=None):
    data_logger = drive_root / "Data Logger"
    try:
        if not data_logger.is_dir():
            return None

        files = [path for path in data_logger.glob("*.ximu3") if path.is_file()]
        if not files:
            return None

        if prefix:
            files = [path for path in files if path.name.startswith(prefix)]

        if not files:
            return None

        files.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
        latest = files[0]
        return SensorItem(f"Data Logger/{latest.name}", latest, "log")
    except OSError:
        return None


def _wait_for_ximu3_drive(timeout_seconds=60, poll_interval=2):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        drive_root = find_ximu3_drive()
        if drive_root is not None:
            return drive_root
        time.sleep(poll_interval)
    return None


def _download_item(item):
    target_dir = Path.cwd()
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = _unique_path(target_dir / item.source.name)

    try:
        shutil.copy2(item.source, target_path)
    except Exception as exc:
        print(f"Download mislukt: {exc}")
        return

    print(f"Opgeslagen als: {target_path}")

    if item.kind == "log" and target_path.suffix.lower() == ".ximu3":
        csv_path = _unique_path(target_path.with_suffix(".csv"))
        converted = _convert_ximu3_to_csv(target_path, csv_path)
        if converted:
            print(f"CSV gemaakt als: {converted}")


def download_latest_sensor_file_to_workdir(timeout_seconds=60, prefix=None):
    print("\nWacht op de x-IMU3 USB-drive...")

    drive_root = _wait_for_ximu3_drive(timeout_seconds=timeout_seconds)
    if drive_root is None:
        print("Geen x-IMU3 USB-drive gevonden binnen de wachttijd.")
        return False

    item = _latest_log_item(drive_root, prefix=prefix)
    if item is None:
        print(f"x-IMU3 gevonden op {drive_root}, maar er is geen nieuw .ximu3-bestand in Data Logger.")
        return False

    _download_item(item)
    print(f"Laatste bestand toegevoegd aan: {Path.cwd().resolve()}")
    return True


def run_sensor_usb_workflow():
    print("\n=== OPTIE 3: x-IMU3 opname op sensor + later downloaden via USB ===")
    print("Deze workflow gebruikt de USB-poort van de sensor.")
    print("Als de sensor wordt losgekoppeld blijft dit programma draaien.")

    try:
        start_new = input("\nNieuwe opname starten op de sensor? [j/n]: ").strip().lower()
        if start_new in {"j", "ja", "y", "yes"}:
            usb_port = _choose_usb_port_from_ports(_list_usb_ports())
            if not usb_port:
                print("Ik zie nu geen USB COM-poort, dus ik sla het starten van een nieuwe opname over.")
                print("Als de sensor later als COM-poort verschijnt, kun je optie 3 opnieuw gebruiken.")
            else:
                prefix = input("Bestandsnaam-prefix voor de opname [Session]: ").strip() or "Session"
                print(f"Start opname op sensor met prefix '{prefix}'...")
                if _send_usb_command(usb_port, {"start": prefix}, "start"):
                    print("Opname gestart.")
                    print("Wanneer je klaar bent kun je de sensor loskoppelen.")
                    print("Als je daarna opnieuw verbindt, stop ik eerst de logging en toon ik daarna de bestanden.")
                    input("Druk op Enter om door te gaan naar de downloadmodus...")

                    stop_now = input("Sensor nog verbonden en logging stoppen voordat je loskoppelt? [j/n]: ").strip().lower()
                    if stop_now in {"j", "ja", "y", "yes"}:
                        _send_usb_command(usb_port, {"stop": None}, "stop")
                        print("Stop-command verstuurd.")
                else:
                    print("Start-command is niet gelukt. Ik ga toch door naar de downloadmodus.")

        print("\nIk wacht nu op de sensor-drive.")
        print("Sluit de sensor weer aan via USB. Als logging nog actief is, stop ik die eerst.")

        while True:
            drive_root = find_ximu3_drive()
            if drive_root is None:
                ports = _list_usb_ports()
                if ports:
                    print("Sensor gevonden als COM-poort, maar nog geen USB-drive.")
                    usb_port = _choose_usb_port_from_ports(ports)
                    if usb_port:
                        stop_choice = input("Logging stoppen zodat de USB-drive zichtbaar wordt? [j/n]: ").strip().lower()
                        if stop_choice in {"j", "ja", "y", "yes"}:
                            if _send_usb_command(usb_port, {"stop": None}, "stop"):
                                print("Stop-command verstuurd. Ik wacht nu tot de drive verschijnt.")
                                time.sleep(2)
                                continue
                            print("Stop-command mislukte. Ik blijf wachten.")
                        else:
                            print("Ik blijf wachten op de drive.")
                else:
                    print("Geen x-IMU3 USB-drive gevonden. Wachten...")
                time.sleep(2)
                continue

            print(f"\nx-IMU3 gevonden op {drive_root}")
            items = _collect_downloadable_items(drive_root)

            if not items:
                print("Geen downloadbare bestanden gevonden. Misschien is de logger nog bezig of is de drive nog niet klaar.")
                time.sleep(2)
                continue

            _print_items(items)

            while True:
                choice = input("\nKies een nummer om te downloaden, r om te verversen, q om te stoppen: ").strip().lower()

                if choice == "q":
                    print("Optie 3 gestopt.")
                    return

                if choice == "r":
                    break

                try:
                    index = int(choice)
                except ValueError:
                    print("Kies een geldig nummer, r of q.")
                    continue

                if not 1 <= index <= len(items):
                    print("Nummer buiten bereik.")
                    continue

                _download_item(items[index - 1])
                break
    except KeyboardInterrupt:
        print("\nOptie 3 afgebroken.")
        return
