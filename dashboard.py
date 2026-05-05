import math
import socket
import time
from collections import deque
from queue import Empty, Queue
from threading import Event, Thread
from pathlib import Path

import matplotlib
import pandas as pd

# Zorg voor een interactieve backend zodat een popup-venster opent.
if matplotlib.get_backend().lower() == "agg":
    for candidate in ("TkAgg", "QtAgg"):
        try:
            matplotlib.use(candidate)
            break
        except Exception:
            continue

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from config import UDP_IP, UDP_PORT, USB_BAUDRATE
from jump_detection import JumpDetector
from record import select_usb_port
from ximu_parser import parse_packet

print("CONFIG UDP_IP =", UDP_IP)
print("CONFIG UDP_PORT =", UDP_PORT)


def _vector_norm(ax, ay, az):
    return math.sqrt(ax * ax + ay * ay + az * az)


def _udp_reader(queue, stop_event, debug=True):
    print(f"Probeer live dashboard te binden op UDP {UDP_IP}:{UDP_PORT}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.bind((UDP_IP, UDP_PORT))
    except OSError as exc:
        print(f"Kan niet binden op UDP {UDP_IP}:{UDP_PORT}")
        print(exc)
        print("\nMogelijke oorzaak:")
        print("- Deze UDP-poort is al in gebruik.")
        print("- Sluit oude test.py/main.py/dashboard.py sessies.")
        print(f"- Check met: netstat -ano | findstr :{UDP_PORT}")
        return

    sock.settimeout(1.0)
    print(f"Live dashboard luistert op UDP {UDP_IP}:{UDP_PORT}")

    try:
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue

            if debug:
                print("\nUDP RAW VAN:", addr)
                print("UDP RAW DATA:", data)
                try:
                    print("UDP ALS TEKST:", data.decode("utf-8", errors="replace").strip())
                except Exception:
                    pass

            parsed = parse_packet(data)

            if parsed:
                if debug:
                    print("UDP PARSED:", parsed)
                queue.put(parsed)
            else:
                if debug:
                    print("UDP NIET HERKEND DOOR PARSER")
    finally:
        sock.close()


def _usb_reader(queue, stop_event, usb_port=None, debug=True):
    try:
        import serial
    except ImportError:
        print("pyserial ontbreekt. Installeer met: pip install pyserial")
        return

    selected_port = usb_port or select_usb_port(None)
    if not selected_port:
        return

    serial_conn = None
    try:
        serial_conn = serial.Serial(selected_port, baudrate=USB_BAUDRATE, timeout=1.0)
        print(f"Live dashboard verbonden met USB {selected_port} @ {USB_BAUDRATE} baud")

        buffer = bytearray()
        while not stop_event.is_set():
            chunk = serial_conn.read(serial_conn.in_waiting or 1)
            if not chunk:
                continue

            buffer.extend(chunk)

            while True:
                newline_index = buffer.find(b"\n")
                if newline_index < 0:
                    break

                data = bytes(buffer[: newline_index + 1])
                del buffer[: newline_index + 1]

                if debug:
                    print("\nUSB RAW DATA:", data)
                    try:
                        print("USB ALS TEKST:", data.decode("utf-8", errors="replace").strip())
                    except Exception:
                        pass

                parsed = parse_packet(data)

                if parsed:
                    if debug:
                        print("USB PARSED:", parsed)
                    queue.put(parsed)
                else:
                    if debug:
                        print("USB NIET HERKEND DOOR PARSER")

    except FileNotFoundError as exc:
        print(f"USB dashboard kon poort {selected_port} niet openen: {exc}")
        print("Probeer de sensor opnieuw los te koppelen en weer aan te sluiten.")
        print("Controleer ook of geen ander programma de COM-poort gebruikt.")
    except Exception as exc:
        print(f"USB dashboardfout: {exc}")
    finally:
        if serial_conn is not None:
            serial_conn.close()


def _replay_reader(queue, stop_event, csv_file, replay_speed=1.0, debug=True):
    source_path = Path(csv_file)

    def _iter_samples():
        if source_path.suffix.lower() == ".csv":
            try:
                df = pd.read_csv(source_path)
            except Exception as exc:
                print(f"Kan CSV niet openen: {exc}")
                return

            required = {"sensor_time", "ax", "ay", "az"}
            missing = required - set(df.columns)
            if missing:
                print("CSV mist kolommen:", missing)
                return

            df = df.dropna(subset=["sensor_time", "ax", "ay", "az"])
            if df.empty:
                print("CSV bevat geen geldige samples.")
                return

            for row in df.itertuples(index=False):
                yield (
                    float(row.sensor_time),
                    float(row.gx) if hasattr(row, "gx") and not pd.isna(row.gx) else 0.0,
                    float(row.gy) if hasattr(row, "gy") and not pd.isna(row.gy) else 0.0,
                    float(row.gz) if hasattr(row, "gz") and not pd.isna(row.gz) else 0.0,
                    float(row.ax),
                    float(row.ay),
                    float(row.az),
                )
            return

        if source_path.suffix.lower() == ".ximu3":
            try:
                with source_path.open("rb") as source_file:
                    for raw_line in source_file:
                        parsed = parse_packet(raw_line)
                        if parsed:
                            yield parsed
            except Exception as exc:
                print(f"Kan ximu3-bestand niet openen: {exc}")
            return

        print("Ondersteunde replay-bestanden zijn .csv en .ximu3")

    previous_time = None
    print(f"Replay dashboard leest: {source_path}")

    for sample in _iter_samples():
        if stop_event.is_set():
            break

        sensor_time, gx, gy, gz, ax, ay, az = sample
        if previous_time is not None:
            delay = max(0.0, (sensor_time - previous_time) / replay_speed)
            if delay > 0:
                time.sleep(delay)

        if debug:
            print("REPLAY SAMPLE:", sample)
        queue.put(sample)
        previous_time = sensor_time


def _build_dashboard_figure(title, source_label, max_samples):
    fig = plt.figure(figsize=(15, 8))
    grid = fig.add_gridspec(2, 2, width_ratios=[3.2, 1.0], height_ratios=[1, 1], wspace=0.12, hspace=0.25)

    ax_gyro = fig.add_subplot(grid[0, 0])
    ax_acc = fig.add_subplot(grid[1, 0], sharex=ax_gyro)
    ax_panel = fig.add_subplot(grid[:, 1])
    ax_panel.axis("off")

    fig.suptitle(f"{title} ({source_label})")

    line_gx, = ax_gyro.plot([], [], label="gx")
    line_gy, = ax_gyro.plot([], [], label="gy")
    line_gz, = ax_gyro.plot([], [], label="gz")
    ax_gyro.set_ylabel("Gyro")
    ax_gyro.grid(True)
    ax_gyro.legend(loc="upper right")

    line_ax, = ax_acc.plot([], [], label="ax")
    line_ay, = ax_acc.plot([], [], label="ay")
    line_az, = ax_acc.plot([], [], label="az")
    takeoff_markers, = ax_acc.plot([], [], "^", color="tab:green", linestyle="None", markersize=7, label="afzet")
    landing_markers, = ax_acc.plot([], [], "x", color="tab:red", linestyle="None", markersize=7, label="landing")
    ax_acc.set_xlabel("Sensor tijd (s)")
    ax_acc.set_ylabel("Accel")
    ax_acc.grid(True)
    ax_acc.legend(loc="upper right")

    stats_text = ax_panel.text(
        0.02,
        0.98,
        "",
        ha="left",
        va="top",
        family="monospace",
        fontsize=10,
    )

    return {
        "fig": fig,
        "ax_gyro": ax_gyro,
        "ax_acc": ax_acc,
        "line_gx": line_gx,
        "line_gy": line_gy,
        "line_gz": line_gz,
        "line_ax": line_ax,
        "line_ay": line_ay,
        "line_az": line_az,
        "takeoff_markers": takeoff_markers,
        "landing_markers": landing_markers,
        "stats_text": stats_text,
        "max_samples": max_samples,
    }


def _run_dashboard(reader, reader_args, source_label, max_samples=600, debug=True):
    max_samples = max(100, int(max_samples))
    data_queue = Queue()
    stop_event = Event()
    detector = JumpDetector()

    reader_thread = Thread(target=reader, args=(data_queue, stop_event, *reader_args), daemon=True)
    reader_thread.start()

    t_values = deque(maxlen=max_samples)
    gx_values = deque(maxlen=max_samples)
    gy_values = deque(maxlen=max_samples)
    gz_values = deque(maxlen=max_samples)
    ax_values = deque(maxlen=max_samples)
    ay_values = deque(maxlen=max_samples)
    az_values = deque(maxlen=max_samples)
    jump_events = deque(maxlen=20)
    total_jump_count = 0

    dashboard = _build_dashboard_figure("x-IMU3 Dashboard", source_label, max_samples)
    fig = dashboard["fig"]
    ax_gyro = dashboard["ax_gyro"]
    ax_acc = dashboard["ax_acc"]
    line_gx = dashboard["line_gx"]
    line_gy = dashboard["line_gy"]
    line_gz = dashboard["line_gz"]
    line_ax = dashboard["line_ax"]
    line_ay = dashboard["line_ay"]
    line_az = dashboard["line_az"]
    takeoff_markers = dashboard["takeoff_markers"]
    landing_markers = dashboard["landing_markers"]
    stats_text = dashboard["stats_text"]

    def on_close(_event):
        stop_event.set()

    fig.canvas.mpl_connect("close_event", on_close)

    def _render_stats():
        thresholds = detector.thresholds()
        rest_level = detector.rest_level
        last_event = jump_events[-1] if jump_events else None

        state_map = {
            "idle": "rust",
            "prejump": "voor-sprong",
            "flight": "in lucht",
            "cooldown": "herstel",
        }

        lines = [
            "Sprongdetectie",
            "--------------",
            f"Bron: {source_label}",
            f"Status: {state_map.get(detector.state, detector.state)}",
            f"Sprongen: {total_jump_count}",
            "",
            "Drempels",
            "--------",
            f"Rust: {rest_level:.3f}" if rest_level is not None else "Rust: n.v.t.",
            f"Takeoff > {thresholds['takeoff']:.3f}" if rest_level is not None else "Takeoff > n.v.t.",
            f"Flight < {thresholds['flight']:.3f}" if rest_level is not None else "Flight < n.v.t.",
            f"Landing > {thresholds['landing']:.3f}" if rest_level is not None else "Landing > n.v.t.",
        ]

        if last_event is not None:
            lines.extend(
                [
                    "",
                    "Laatste sprong",
                    "-------------",
                    f"Flight: {last_event.flight_duration:.3f} s",
                    f"Takeoff: {last_event.takeoff_time:.3f} s",
                    f"Landing: {last_event.landing_time:.3f} s",
                ]
            )

        stats_text.set_text("\n".join(lines))

    def update(_frame):
        nonlocal total_jump_count
        updated = False

        while True:
            try:
                sensor_time, gx, gy, gz, ax, ay, az = data_queue.get_nowait()
            except Empty:
                break

            t_values.append(sensor_time)
            gx_values.append(gx)
            gy_values.append(gy)
            gz_values.append(gz)
            ax_values.append(ax)
            ay_values.append(ay)
            az_values.append(az)
            updated = True

            event = detector.update(sensor_time, ax, ay, az)
            if event is not None:
                jump_events.append(event)
                total_jump_count += 1
                updated = True

        if len(t_values) >= 2:
            line_gx.set_data(t_values, gx_values)
            line_gy.set_data(t_values, gy_values)
            line_gz.set_data(t_values, gz_values)
            line_ax.set_data(t_values, ax_values)
            line_ay.set_data(t_values, ay_values)
            line_az.set_data(t_values, az_values)

            ax_gyro.set_xlim(t_values[0], t_values[-1])
            ax_acc.set_xlim(t_values[0], t_values[-1])

            ax_gyro.relim()
            ax_gyro.autoscale_view(scalex=False, scaley=True)
            ax_acc.relim()
            ax_acc.autoscale_view(scalex=False, scaley=True)

        if jump_events:
            takeoff_markers.set_data(
                [event.takeoff_time for event in jump_events],
                [event.takeoff_peak for event in jump_events],
            )
            landing_markers.set_data(
                [event.landing_time for event in jump_events],
                [event.landing_peak for event in jump_events],
            )
        else:
            takeoff_markers.set_data([], [])
            landing_markers.set_data([], [])

        _render_stats()

        if not updated and not jump_events:
            return [
                line_gx,
                line_gy,
                line_gz,
                line_ax,
                line_ay,
                line_az,
                takeoff_markers,
                landing_markers,
            ]

        return [
            line_gx,
            line_gy,
            line_gz,
            line_ax,
            line_ay,
            line_az,
            takeoff_markers,
            landing_markers,
        ]

    animation = FuncAnimation(fig, update, interval=50, blit=False, cache_frame_data=False)

    try:
        plt.tight_layout()
        plt.show()
    finally:
        stop_event.set()
        reader_thread.join(timeout=2.0)
        del animation


def run_live_dashboard(transport="udp", usb_port=None, max_samples=600, debug=True):
    transport = transport.lower().strip()
    if transport not in {"udp", "usb"}:
        raise ValueError("transport moet 'udp' of 'usb' zijn")

    if transport == "udp":
        _run_dashboard(_udp_reader, (debug,), "live UDP", max_samples=max_samples, debug=debug)
        return

    if usb_port is None:
        usb_port = select_usb_port(None)
        if not usb_port:
            return

    _run_dashboard(_usb_reader, (usb_port, debug), f"live USB {usb_port}", max_samples=max_samples, debug=debug)


def run_file_dashboard(csv_file, replay_speed=1.0, max_samples=600, debug=True):
    csv_path = Path(csv_file)
    if replay_speed <= 0:
        raise ValueError("replay_speed moet groter zijn dan 0")

    _run_dashboard(
        _replay_reader,
        (csv_path, replay_speed, debug),
        f"replay {csv_path.name}",
        max_samples=max_samples,
        debug=debug,
    )


if __name__ == "__main__":
    run_live_dashboard(transport="udp")
