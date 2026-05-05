# Functionaliteiten en losse onderdelen

Dit bestand beschrijft wat de app kan en welk bestand waarvoor verantwoordelijk is.

## Hoofdfuncties van de app

- Live dashboard via UDP
- Live dashboard via USB
- Data opnemen naar CSV
- Opname op de sensor starten
- Opname op de sensor stoppen
- Laatste sensorbestand downloaden naar de werkmap
- Dashboard replay op basis van CSV of `.ximu3`
- Sprongdetectie in live data en in bestanden
- Grafieken opslaan als PNG

## Bestanden en verantwoordelijkheden

| Bestand | Rol |
| --- | --- |
| `main.py` | Startpunt van de app. Toont het menu en koppelt alle onderdelen aan elkaar. |
| `config.py` | Centrale instellingen zoals UDP-poort, USB-baudrate en bestandsnamen. |
| `ximu_parser.py` | Zet ruwe x-IMU3 packets om naar een vaste sample-structuur. |
| `record.py` | Neemt data op uit UDP of USB en schrijft een CSV-bestand. |
| `dashboard.py` | Laat live data of replay-data zien in een grafisch venster. |
| `sensor_logger.py` | Start en stopt onboard logging op de sensor en downloadt het nieuwste bestand. |
| `analysis.py` | Doet batch-analyse op CSV-bestanden en maakt plots. |
| `jump_detection.py` | Bevat de gedeelde sprongdetector die live en offline wordt gebruikt. |
| `requirements.txt` | Lijst van Python libraries die nodig zijn voor het project. |

## Detail per onderdeel

### `ximu_parser.py`

- Ondersteunt ASCII packets
- Ondersteunt binary packets
- Geeft altijd terug:

```text
(sensor_time, gx, gy, gz, ax, ay, az)
```

### `record.py`

- Leest data via UDP of USB
- Schrijft elke geldige sample weg naar CSV
- Gebruikt dezelfde parser als de rest van de app

### `dashboard.py`

- Toont gyro en acceleratie
- Werkt live met UDP
- Werkt live met USB
- Kan bestanden afspelen als replay
- Markeert sprongen in de grafiek
- Houdt een teller bij

### `sensor_logger.py`

- Stuurt start en stop naar de sensor via USB
- Leest de actuele sensorstatus waar mogelijk uit
- Downloadt de nieuwste `.ximu3`-file naar de huidige werkmap
- Zet daarna automatisch om naar CSV als dat lukt

### `analysis.py`

- Plot acceleratie
- Telt simpele events
- Telt sprongen met dezelfde detector als het dashboard

### `jump_detection.py`

- Bevat de herbruikbare state machine voor sprongen
- Gebruikt acceleratie-norm
- Herkent afzet, flight en landing

## Bestanden die je meestal niet in Git wilt zetten

- `__pycache__/`
- `*.pyc`
- `.ximu3_session.json`
- gegenereerde plots zoals `*.png`
- gegenereerde data zoals `*.csv`
- gedownloade sensorlogs in een lokale `downloads/` map

## Files die wel in Git horen

- alle `.py` bronbestanden
- `requirements.txt`
- `README.md`
- `HANDOUT.md`
- `FUNCTIONALITEITEN.md`
- `.gitignore`

## Handig als je deelnemers stukjes van de puzzel geeft

- Geef eerst `ximu_parser.py` als de ruwe data nog niet werkt.
- Geef `record.py` als data wel binnenkomt maar nog niet wordt opgeslagen.
- Geef `dashboard.py` als de data live zichtbaar moet worden.
- Geef `sensor_logger.py` als logging op de sensor zelf nog ontbreekt.
- Geef `jump_detection.py` als de visualisatie al werkt maar het tellen van sprongen nog niet goed genoeg is.
