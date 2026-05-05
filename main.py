from pathlib import Path

from analysis import count_events, plot_acceleration
from analysis import count_jumps
from config import CSV_FILE, RECORD_SECONDS
from dashboard import run_file_dashboard, run_live_dashboard
from record import record_data
from sensor_logger import start_sensor_logging, stop_sensor_logging


def choose_transport():
    print("\nKies connectievorm:")
    print("  1. UDP (Wi-Fi)")
    print("  2. USB (COM)")

    while True:
        choice = input("Maak een keuze [1/2]: ").strip()
        if choice == "1":
            return "udp"
        if choice == "2":
            return "usb"
        print("Kies 1 of 2.")


def choose_mode():
    print("\nKies wat je wilt doen:")
    print("  1. Alleen live dashboard")
    print("  2. Data opnemen + analyse")
    print("  3. Opname op sensor starten (prefix + reset)")
    print("  4. Opname op sensor stoppen + laatste file naar werkmap")
    print("  5. Dashboard op bestand (CSV of XIMU3 replay)")

    while True:
        choice = input("Maak een keuze [1/2/3/4/5]: ").strip()
        if choice in {"1", "2", "3", "4", "5"}:
            return choice
        print("Kies 1, 2, 3, 4 of 5.")


def choose_replay_file():
    files = list(Path.cwd().glob("*.csv")) + list(Path.cwd().glob("*.ximu3"))
    files = sorted(
        {path.resolve(): path for path in files}.values(),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        print("Geen CSV- of XIMU3-bestanden gevonden in de werkmap.")
        return None

    print("\nBeschikbare replay-bestanden:")
    for index, path in enumerate(files[:15], start=1):
        print(f"  {index}. {path.name}")

    choice = input("Kies bestandsnummer [Enter = nieuwste]: ").strip()
    if not choice:
        return files[0]

    try:
        idx = int(choice)
    except ValueError:
        print("Ongeldige keuze.")
        return None

    if not 1 <= idx <= min(len(files), 15):
        print("Nummer buiten bereik.")
        return None

    return files[idx - 1]


def main():
    mode = choose_mode()

    if mode == "1":
        transport = choose_transport()
        run_live_dashboard(transport=transport, debug=True)
        return

    if mode == "2":
        transport = choose_transport()
        print("\n=== START OPNAME ===")
        record_data(
            duration_seconds=RECORD_SECONDS,
            output_file=CSV_FILE,
            transport=transport,
            debug=True,
        )

        print("\n=== PLOTTEN ===")
        plot_acceleration(CSV_FILE)

        print("\n=== ANALYSE ===")
        count_events(CSV_FILE)
        count_jumps(CSV_FILE)
        return

    if mode == "3":
        start_sensor_logging()
        return

    if mode == "4":
        stop_sensor_logging()
        return

    if mode == "5":
        replay_file = choose_replay_file()
        if replay_file is None:
            return

        speed_text = input("Replay-snelheid [1.0]: ").strip()
        try:
            replay_speed = float(speed_text) if speed_text else 1.0
        except ValueError:
            print("Ongeldige snelheid, gebruik 1.0.")
            return

        if replay_speed <= 0:
            print("Replay-snelheid moet groter zijn dan 0.")
            return

        run_file_dashboard(str(replay_file), replay_speed=replay_speed, debug=True)
        return


if __name__ == "__main__":
    main()
