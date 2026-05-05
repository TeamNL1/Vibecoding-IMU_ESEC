# Handout: van sensor naar live dashboard en sprongdetectie

Deze handout is bedoeld als bouwplan voor een Vibecode-sessie. Deelnemers kunnen stap voor stap een werkende x-IMU3-app bouwen.

## Einddoel

Aan het einde van de sessie kan de app:

- live data tonen via Wi-Fi of USB
- data opnemen naar een CSV-bestand
- logging op de sensor zelf starten en stoppen
- bestanden van de sensor downloaden naar de werkmap
- een replay-dashboard tonen op basis van CSV of `.ximu3`
- sprongen tellen en markeren in de grafiek

## Wat je nodig hebt

- Een laptop met Windows
- Python 3.11 of nieuwer
- Een x-IMU3 sensor
- Een USB-kabel voor de sensor
- Een Wi-Fi setup als je ook live UDP wilt gebruiken

## Stap 1: Python installeren

1. Ga naar de officiële Python website.
2. Download Python 3.11 of nieuwer.
3. Vink tijdens de installatie aan dat Python aan `PATH` wordt toegevoegd.
4. Controleer daarna:

```bash
python --version
```

## Stap 2: Project openen

1. Zet de projectmap op je computer.
2. Open die map in VS Code.
3. Controleer dat de bestanden zichtbaar zijn:

- `main.py`
- `config.py`
- `record.py`
- `dashboard.py`
- `analysis.py`
- `jump_detection.py`
- `sensor_logger.py`
- `ximu_parser.py`
- `requirements.txt`

## Stap 3: Virtuele omgeving maken

Gebruik een virtuele omgeving zodat iedereen met dezelfde libraries werkt.

```bash
python -m venv .venv
```

Activeer daarna de omgeving in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Als PowerShell moeilijk doet met policies, gebruik dan de VS Code terminal of een andere shell die Python wel mag activeren.

## Stap 4: Libraries installeren

Installeer de benodigde pakketten:

```bash
pip install -r requirements.txt
```

De kernlibraries zijn:

- `matplotlib`
- `pandas`
- `scipy`
- `pyserial`

## Stap 5: Sensor instellen

Voor live Wi-Fi data:

1. Zet in de x-IMU3 software de `Send Port` gelijk aan de poort in `config.py`.
2. In dit project is dat standaard `9000`.
3. Zorg dat de laptop bereikbaar is op `0.0.0.0` via die poort.

Voor USB:

1. Sluit de sensor via USB aan.
2. Controleer dat Windows een COM-poort laat zien.
3. Laat het programma de juiste poort kiezen als daarom wordt gevraagd.

## Stap 6: De parser bouwen

Doel:

- ruwe packets van de x-IMU3 omzetten naar vaste data

Bestand:

- `ximu_parser.py`

Taken:

- ASCII packets lezen
- binary packets lezen
- altijd teruggeven:

```text
sensor_time, gx, gy, gz, ax, ay, az
```

## Stap 7: Data opnemen naar CSV

Doel:

- live data opslaan naar een CSV-bestand

Bestand:

- `record.py`

Taken:

- verbinding maken via UDP of USB
- packets parseren
- CSV-header schrijven
- elke sample als rij opslaan

## Stap 8: Live dashboard bouwen

Doel:

- data in real time laten zien

Bestand:

- `dashboard.py`

Taken:

- data uit UDP of USB lezen
- grafieken bijwerken
- gyro en acceleratie tonen
- sprongen markeren
- een teller tonen voor het aantal sprongen

## Stap 9: Opname op de sensor

Doel:

- logging direct op de x-IMU3 starten en stoppen

Bestand:

- `sensor_logger.py`

Taken:

- start-commando versturen
- stop-commando versturen
- sensorbestanden downloaden naar de werkmap
- nieuwste `.ximu3`-file herkennen

## Stap 10: Analyse en sprongdetectie

Doel:

- achteraf op een bestand dezelfde analyse doen als live

Bestanden:

- `analysis.py`
- `jump_detection.py`

Taken:

- sprongdetectie delen tussen live en replay
- sprongen tellen
- flight time uitrekenen
- grafiek met sprongmarkeringen maken

## Stap 11: Hoofdmenu maken

Doel:

- alle losse onderdelen samenbrengen in een simpele user flow

Bestand:

- `main.py`

Taken:

- menu tonen
- gebruiker laten kiezen tussen live, opnemen, sensor logging en replay
- de juiste module aanroepen

## Suggestie voor een workshop-opbouw

Je kunt deze onderdelen ook als puzzelstukken geven:

1. Groep 1: parser
2. Groep 2: opnemen naar CSV
3. Groep 3: dashboard
4. Groep 4: sensor logging via USB
5. Groep 5: replay en sprongdetectie

## Eindcheck

Als alles werkt, moet dit mogelijk zijn:

1. Sensor aansluiten
2. Live data zien
3. Opnemen naar CSV
4. Sensor zelf laten loggen
5. Bestand downloaden naar de werkmap
6. Replay starten
7. Sprongen tellen en zichtbaar markeren
