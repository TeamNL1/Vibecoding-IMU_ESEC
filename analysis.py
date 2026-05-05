import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from jump_detection import JumpDetector


def _load_csv(csv_file):
    df = pd.read_csv(csv_file)

    if df.empty:
        print(f"CSV-bestand is leeg: {csv_file}")
        return df

    required = {"sensor_time", "ax", "ay", "az"}
    missing = required - set(df.columns)
    if missing:
        print("CSV mist kolommen:", missing)
        return pd.DataFrame()

    df = df.dropna(subset=["sensor_time", "ax", "ay", "az"])
    return df


def plot_acceleration(csv_file="ximu3_data.csv", output_png="acceleration_plot.png"):
    df = _load_csv(csv_file)
    if df.empty:
        print("Geen data om te plotten.")
        return

    df["acc_norm"] = np.sqrt(df["ax"] ** 2 + df["ay"] ** 2 + df["az"] ** 2)

    plt.figure(figsize=(12, 6))
    plt.plot(df["sensor_time"], df["ax"], label="ax")
    plt.plot(df["sensor_time"], df["ay"], label="ay")
    plt.plot(df["sensor_time"], df["az"], label="az")
    plt.plot(df["sensor_time"], df["acc_norm"], label="acc_norm", linewidth=2)

    plt.xlabel("Sensor tijd (s)")
    plt.ylabel("Acceleratie")
    plt.title("x-IMU3 acceleratie")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_png, dpi=150)
    plt.show()

    print(f"Grafiek opgeslagen als: {output_png}")


def count_events(csv_file="ximu3_data.csv", output_png="events_plot.png"):
    try:
        from scipy.signal import find_peaks
    except ImportError:
        print("scipy ontbreekt. Installeer met: pip install scipy")
        return

    df = _load_csv(csv_file)
    if df.empty:
        print("Geen data voor event-detectie.")
        return

    df["acc_norm"] = np.sqrt(df["ax"] ** 2 + df["ay"] ** 2 + df["az"] ** 2)

    if df["acc_norm"].dropna().empty:
        print("acc_norm bevat geen geldige waarden.")
        return

    threshold = df["acc_norm"].mean() + df["acc_norm"].std()

    if np.isnan(threshold):
        print("Drempelwaarde is NaN. Te weinig geldige data.")
        return

    peaks, _properties = find_peaks(
        df["acc_norm"],
        height=threshold,
        distance=10,
    )

    print("\nResultaat simpele metric")
    print("------------------------")
    print(f"Drempelwaarde: {threshold}")
    print(f"Aantal gevonden pieken/events: {len(peaks)}")

    plt.figure(figsize=(12, 6))
    plt.plot(df["sensor_time"], df["acc_norm"], label="acc_norm")
    plt.plot(
        df["sensor_time"].iloc[peaks],
        df["acc_norm"].iloc[peaks],
        "x",
        label="pieken",
    )
    plt.axhline(threshold, linestyle="--", label="drempel")

    plt.xlabel("Sensor tijd (s)")
    plt.ylabel("Acceleratie norm")
    plt.title(f"Events/pieken: {len(peaks)}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_png, dpi=150)
    plt.show()

    print(f"Event-grafiek opgeslagen als: {output_png}")


def count_jumps(csv_file="ximu3_data.csv", output_png="jump_events_plot.png"):
    df = _load_csv(csv_file)
    if df.empty:
        print("Geen data voor sprongdetectie.")
        return

    detector = JumpDetector()
    events = []

    df["acc_norm"] = np.sqrt(df["ax"] ** 2 + df["ay"] ** 2 + df["az"] ** 2)

    for row in df.itertuples(index=False):
        event = detector.update(
            float(row.sensor_time),
            float(row.ax),
            float(row.ay),
            float(row.az),
        )
        if event is not None:
            events.append(event)

    print("\nSprongdetectie")
    print("--------------")
    print(f"Aantal gevonden sprongen: {len(events)}")

    if events:
        durations = [event.flight_duration for event in events]
        avg_duration = float(np.mean(durations))
        print(f"Gemiddelde flight time: {avg_duration:.3f} s")

    plt.figure(figsize=(12, 6))
    plt.plot(df["sensor_time"], df["acc_norm"], label="acc_norm")

    if events:
        takeoff_times = [event.takeoff_time for event in events]
        takeoff_peaks = [event.takeoff_peak for event in events]
        landing_times = [event.landing_time for event in events]
        landing_peaks = [event.landing_peak for event in events]

        plt.scatter(takeoff_times, takeoff_peaks, marker="^", s=60, label="afzet")
        plt.scatter(landing_times, landing_peaks, marker="x", s=60, label="landing")

    plt.xlabel("Sensor tijd (s)")
    plt.ylabel("Acceleratie norm")
    plt.title(f"Sprongdetectie: {len(events)} sprongen")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_png, dpi=150)
    plt.show()

    print(f"Spronggrafiek opgeslagen als: {output_png}")
