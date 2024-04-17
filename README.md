Krefia API
=========

### Deze api levert de volgende data:

- Overzicht meldingen uit schuldhulpportaal
- Overzicht leningen
- Overzciht shldhulpdossiers

### Local env
```
python -m venv venv
source venv/bin/activate
pip install -r requirements-root.txt

// unittest
python -m unittest

// requirements.txt maken
make requirements

// dev server
sh scripts/run-dev.sh
```

### Kenmerken
- Het bronsysteem is Allegro
- Het bronsysteem wordt bevraagd op basis van een BSN.
- De output van de api is JSON formaat.

### Development & testen
- Er is geen uitgebreide lokale set-up waarbij ontwikkeld kan worden op basis van een "draaiende" api. Dit zou gemaakt / geïmplementeerd moeten worden.
- Alle tests worden dichtbij de geteste functionaliteit opgeslagen. B.v `some_service.py` en wordt getest in `test_some_service.py`.

### CI/CD
- De applicatie wordt verpakt in een Docker container.
- Bouwen en deployen van de applicatie gebeurt in Github en Azure DevOps.

### Release to production
```
~ cd scripts
~ sh release.sh --minor [--major [--patch]]
```
