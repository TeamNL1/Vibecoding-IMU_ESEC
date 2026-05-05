"""
Parser voor x-IMU3 data.

Ondersteunt voorlopig:
1. ASCII packet met meerdere regels:
   I,timestamp,gx,gy,gz,ax,ay,az
   A,timestamp,ax,ay,az
   ... plus eventuele extra regels zoals L/H/M
2. Binary inertial message:
   0xC9 + timestamp uint32 little-endian + floats + LF

Return-formaat:
(sensor_time, gx, gy, gz, ax, ay, az)

Als gyro niet beschikbaar is, wordt gx/gy/gz = 0.0.
"""

import struct


def parse_inertial_ascii(line):
    line = line.strip()
    if not line:
        return None

    parts = [p.strip() for p in line.split(",")]
    tag = parts[0] if parts else ""

    # Verwacht: I, timestamp, gx, gy, gz, ax, ay, az
    if tag == "I" and len(parts) >= 8:
        try:
            sensor_time = float(parts[1]) / 1_000_000.0
            gx = float(parts[2])
            gy = float(parts[3])
            gz = float(parts[4])
            ax = float(parts[5])
            ay = float(parts[6])
            az = float(parts[7])
            return sensor_time, gx, gy, gz, ax, ay, az
        except ValueError:
            return None

    # Verwacht: A, timestamp, ax, ay, az
    if tag == "A" and len(parts) >= 5:
        try:
            sensor_time = float(parts[1])
            ax = float(parts[2])
            ay = float(parts[3])
            az = float(parts[4])
            return sensor_time, 0.0, 0.0, 0.0, ax, ay, az
        except ValueError:
            return None

    return None


def parse_ascii_packet(data):
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None

    for line in text.splitlines():
        parsed = parse_inertial_ascii(line)
        if parsed:
            return parsed

    return None


def parse_inertial_binary(data):
    # x-IMU3 binary inertial message:
    # [0xC9][timestamp uint32 little-endian][6 float32][LF]
    if len(data) < 30:
        return None
    if data[0] != 0xC9:
        return None

    raw = data
    if raw[-1] == 0x0A:
        raw = raw[:-1]

    try:
        sensor_time = struct.unpack_from("<I", raw, 1)[0] / 1_000_000.0
        payload = raw[5:]
        if len(payload) < 24:
            return None
        usable_len = (len(payload) // 4) * 4
        values = struct.unpack("<" + "f" * (usable_len // 4), payload[:usable_len])
        if len(values) < 6:
            return None
        gx, gy, gz, ax, ay, az = values[:6]
        return sensor_time, gx, gy, gz, ax, ay, az
    except struct.error:
        return None


def parse_packet(data):
    """Probeert eerst ASCII-regels in het packet, daarna binary."""
    parsed = parse_ascii_packet(data)
    if parsed:
        return parsed

    return parse_inertial_binary(data)
