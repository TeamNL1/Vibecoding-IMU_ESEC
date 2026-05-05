# Git repo checklist

Dit is de minimale set om het project netjes in Git te zetten.

## In de repo opnemen

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
- `.gitignore`

## Meestal niet opnemen

- `__pycache__/`
- `*.pyc`
- `.ximu3_session.json`
- `downloads/`
- gegenereerde `*.csv` bestanden
- gegenereerde `*.png` grafieken
- tijdelijke sensor exports zoals `*.ximu3`

## Aanbevolen Git-flow

```bash
git init
git add .
git commit -m "Initial x-IMU3 vibecode project"
```

Als je een schone demo-repo wilt, commit dan alleen broncode en documentatie.
Laat ruwe meetdata en gegenereerde afbeeldingen buiten Git.
