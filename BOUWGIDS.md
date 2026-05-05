# Bouwgids: van idee naar een x-IMU3 vibecode app

Dit document beschrijft hoe je stap voor stap een app bouwt die data uit een X-IMU3 sensor leest en inzichtelijk maakt via een dashboard.
Het is bedoeld voor een hackathon of workshop waarin deelnemers zelf vibecodend een werkend product maken.

## Link naar documentatie van X-IMU
https://x-io.co.uk/x-imu3/#downloads
Deze is belangrijk als voedingsbodem voor je AI hulpmiddel

## Doel van het eindproduct

De app moet uiteindelijk kunnen:

- live data van een x-IMU3 ontvangen via Wi-Fi of USB
- data opslaan naar CSV
- live een dashboard tonen
- logging op de sensor zelf starten en stoppen
- bestanden van de sensor naar de laptop kopiëren
- data opnieuw afspelen vanuit een bestand
- sprongen detecteren en tellen

## Bouwprincipe

Werk niet meteen aan alles tegelijk.
Bouw het product in kleine lagen zodat elke laag zelfstandig werkt.
Gebruik AI niet alleen om te bouwen maar ook om mee te denken in logische structuren en om uitleg te geven over waarom je bepaalde dingen doet.

Aanbevolen volgorde:

1. projectsetup
2. `main.py` als startpunt neerzetten, dit is nodig om modulair andere stukken van de software makkelijk te kunnen toevoegen
3. centrale instellingen maken, in dit document maak pas je de instellingen voor je sensor aan
4. ruwe data inlezen
5. data opslaan
6. dashboard tekenen
7. sensorlogging via USB
8. replay vanaf bestand
9. sprongdetectie
10. alles verder uitbouwen vanuit `main.py`

## Stap 1: project starten

Maak eerst een leeg Python-project.

Benodigd:

- Python 3.11 of nieuwer
- VS Code of een andere editor
- `pip`

Maak een virtuele omgeving:

```bash
python -m venv .venv
```

Installeer daarna de libraries:

```bash
pip install matplotlib pandas scipy pyserial
```

Later kun je dit vastzetten in `requirements.txt`.

## Stap 2: main.py als kapstok maken

Maak meteen een klein `main.py` met een menu en lege functies of placeholders.

Waarom dit vroeg handig is:

- je werkt vanaf het begin vanuit één startpunt
- je kunt per stap steeds iets nieuws aan hetzelfde menu toevoegen
- de app voelt direct als één geheel in plaats van losse scripts

Start bijvoorbeeld met een simpele keuze tussen:

- live dashboard
- opnemen
- sensor logging
- replay

In het begin mogen die opties nog alleen een `print()` doen of naar een placeholder verwijzen.
Later vul je de echte functionaliteit stap voor stap in.

## Stap 3: centrale instellingen maken

Maak een `config.py` met alle vaste waarden.

Zet daar bijvoorbeeld in:

- UDP IP
- UDP poort
- USB baudrate
- standaard CSV-bestand
- recordduur

Waarom dit nuttig is:

- je hoeft instellingen maar op één plek aan te passen
- de hele app blijft overzichtelijk
- je hoeft niet in vijf bestanden hetzelfde getal te wijzigen

## Stap 4: parser voor x-IMU3 packets bouwen

Maak een losse module die ruwe data omzet naar een vaste samplevorm.

Bestand:

- `ximu_parser.py`

De parser moet uiteindelijk iets teruggeven als:

```text
(sensor_time, gx, gy, gz, ax, ay, az)
```

Waarom dit de eerste echte inhoudelijke stap is:

- alle latere modules kunnen dan dezelfde datastructuur gebruiken
- het maakt niet uit of de bron UDP, USB, CSV of replay is

## Stap 5: een recorder bouwen

Maak nu een module die samples wegschrijft naar CSV.

Bestand:

- `record.py`

Deze module moet:

- verbinding maken via UDP of USB
- packets lezen
- de parser aanroepen
- een CSV-header schrijven
- elke geldige sample als rij opslaan

Dit is vaak de eerste zichtbare mijlpaal voor deelnemers:

- er komt echte data binnen
- die data wordt opgeslagen
- je hebt iets wat je later weer kunt analyseren

## Stap 6: een eerste dashboard tekenen

Maak daarna een eenvoudige visualisatie.

Bestand:

- `dashboard.py`

Begin klein:

- plot alleen acceleratie
- daarna gyro
- daarna de grafiek live laten updaten

Pas als dat werkt, voeg je extra polish toe zoals:

- meerdere assen
- labels
- legenda
- titels

Belangrijk:

- gebruik dezelfde samplevorm als in de parser
- laat het dashboard los staan van het transport

## Stap 7: USB-opname op de sensor

Voeg nu een module toe die logging op de sensor zelf aanstuurt.

Bestand:

- `sensor_logger.py`

De logica hier:

- start logging op de x-IMU3
- stop logging op de x-IMU3
- herken de nieuwste `.ximu3`-file
- kopieer die naar de werkmap

Waarom deze stap apart hoort:

- dit is een ander soort workflow dan live streamen
- het blijft duidelijker als recording, download en dashboard gescheiden blijven

## Stap 8: replay vanuit bestand

Nu kun je dezelfde data-pipeline opnieuw gebruiken voor bestanden.

Bestand:

- `dashboard.py`

Voeg een replay-mode toe die:

- CSV-bestanden leest
- of `.ximu3`-bestanden leest
- dezelfde samplestructuur gebruikt als live data
- de data met een tempo afspeelt

Dit is een belangrijke architectuurles:

- live data en bestanddata moeten dezelfde verwerkingslaag gebruiken
- anders bouw je dubbele logica

## Stap 9: sprongdetectie maken

Voeg daarna een aparte module toe voor jump detection.

Bestand:

- `jump_detection.py`

Maak hier een kleine state machine in plaats van één losse drempel.

Bijvoorbeeld states zoals:

- idle
- prejump
- flight
- cooldown

Waarom dit beter werkt:

- je voorkomt dubbel tellen
- je kunt afzet en landing apart herkennen
- je kunt dezelfde detector live en offline gebruiken

## Stap 10: analyse voor bestanden

Maak een analysemodule die CSV-bestanden achteraf verwerkt.

Bestand:

- `analysis.py`

Taken:

- grafieken maken
- simpele events tellen
- sprongen tellen
- resultaten opslaan als PNG

Gebruik hier dezelfde detector als in het dashboard.

## Stap 11: alles verder uitbouwen vanuit `main.py`

Breid het startpunt steeds verder uit.

Bestand:

- `main.py`

Het menu kan bijvoorbeeld deze keuzes hebben:

1. live dashboard
2. opnemen + analyse
3. opname op sensor starten
4. opname op sensor stoppen
5. replay dashboard op bestand

Waarom een menu handig is:

- deelnemers zien meteen hoe de app in lagen is opgebouwd
- je kunt per onderdeel testen
- je hoeft niet telkens code aan te passen om iets anders te starten

## Aanbevolen workshop-opzet

Als je dit tijdens een hackathon wilt laten bouwen, kun je de groepjes zo verdelen:

### Groep A: data inlezen

Doel:

- UDP of USB packets ontvangen
- parser werkend krijgen

### Groep A2: main.py

Doel:

- het menu en de flow bewaken
- placeholders toevoegen voor nieuwe functies
- modules steeds stap voor stap aansluiten

### Groep B: data opslaan

Doel:

- CSV-output maken
- headers en kolommen goed zetten

### Groep C: visualisatie

Doel:

- live dashboard maken
- grafiek laten updaten

### Groep D: sensor logging

Doel:

- start en stop via USB
- bestanden downloaden naar laptop

### Groep E: replay en sprongdetectie

Doel:

- bestanden afspelen
- sprongen tellen en markeren

## Ontwerpregels

1. Houd transport en verwerking gescheiden.
2. Laat alle modules dezelfde samplevorm gebruiken.
3. Maak features klein en testbaar.
4. Bouw eerst zonder extra franje.
5. Voeg pas daarna kleuren, labels en visual polish toe.

## Wat je uiteindelijk in de repo wilt hebben

- `main.py`
- `config.py`
- `ximu_parser.py`
- `record.py`
- `dashboard.py`
- `sensor_logger.py`
- `analysis.py`
- `jump_detection.py`
- `requirements.txt`
- `README.md`
- `HANDOUT.md`
- `BOUWGIDS.md`
- `FUNCTIONALITEITEN.md`
- `GIT_REPO_CHECKLIST.md`
- `.gitignore`
