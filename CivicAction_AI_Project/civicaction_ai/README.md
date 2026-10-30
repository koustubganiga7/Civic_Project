# CivicAction AI — From Complaints to Action

A hackathon prototype for collecting civic complaints, analysing them transparently, identifying repeated locations, and tracking authority action.

## Technology
- Python + Flask
- SQLite
- HTML, CSS, JavaScript
- Leaflet + OpenStreetMap for map display

## Run locally
1. Install Python 3.10 or later.
2. Open a terminal in this project folder.
3. Create a virtual environment (optional but recommended):
   - Windows: `py -m venv venv`
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv venv` then `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start: `python app.py`
6. Open `http://127.0.0.1:5000`

The SQLite database `civic.db` is created automatically.

## Main routes
- `/` Dashboard
- `/report` Submit a complaint
- `/track` Track using complaint ID
- `/admin` Authority workflow panel

## AI approach and honesty note
This prototype uses transparent keyword rules for category and priority suggestions, a short extractive summary, and `difflib.SequenceMatcher` text similarity for possible duplicate detection. It is not a trained machine-learning model or a production-grade NLP system. Results can be wrong, so authorities must review suggestions. Location hotspot counts are grouped by the location text supplied by citizens; they are not a geographic clustering algorithm. The map uses coordinates only when users provide latitude and longitude.

## Demo data
Submit 30–50 synthetic complaints with repeated locations, repeated descriptions, and a few safety-related examples. Do not enter real personal data.

## Limitations before real deployment
- Add authentication, role-based authorization and audit logs.
- Validate and geocode addresses safely.
- Use a trained NLP/embedding model and evaluate it on representative local-language data.
- Improve duplicate matching with geospatial distance and semantic similarity.
- Add privacy, retention, consent and secure image-handling policies.
- Use HTTPS, production server settings and environment-based secrets.
- Map tiles require an internet connection.
