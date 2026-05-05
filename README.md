# x-IMU3 Vibecode Project

Dit project laat zien hoe je met een x-IMU3 sensor data kunt:

- live bekijken via een dashboard
- lokaal opnemen naar CSV
- op de sensor zelf loggen en later downloaden
- replayen vanuit CSV of `.ximu3`
- sprongen detecteren in live data en in bestanden

## Snel starten

1. Installeer Python 3.11 of nieuwer.
2. Open een terminal in deze map.
3. Maak een virtuele omgeving:

```bash
python -m venv .venv
```

4. Activeer de virtuele omgeving.
5. Installeer de dependencies:

```bash
pip install -r requirements.txt
```

6. Start de app:

```bash
python main.py
```

## Belangrijkste bestanden

- `main.py` - menu en workflow.
- `config.py` - centrale instellingen.
- `record.py` - data opnemen naar CSV via UDP of USB.
- `sensor_logger.py` - opname op de sensor starten, stoppen en downloaden.
- `dashboard.py` - live dashboard en replay-dashboard.
- `analysis.py` - grafieken en batch-analyse van bestanden.
- `jump_detection.py` - gedeelde sprongdetectie.
- `ximu_parser.py` - parser voor x-IMU3 packets.
- `requirements.txt` - Python libraries.

## Menu in de app

1. Alleen live dashboard
2. Data opnemen + analyse
3. Opname op sensor starten
4. Opname op sensor stoppen + laatste file naar werkmap
5. Dashboard op bestand als replay

## Git-advies

Deze repo bevat alleen broncode, instellingen en documentatie.
Gegenereerde bestanden zoals logs, plots en cachebestanden horen niet in Git.
