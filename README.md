# EcoSort AI

A campus waste-sorting assistant, built for the **1M1B Internship on Green
Skills & Applied AI for Climate Action** (Govt. of Karnataka × Microsoft ×
MeitY Startup Hub). It covers all four layers the brief asks for — frontend,
backend, database, and computer vision — on top of the real
`Eco-Sort-Cleaned` dataset.

## What it does

1. **Scan** — point your camera (or upload a photo) at a waste item. A
   pretrained MobileNet vision model, running entirely in your browser,
   identifies the object. The backend maps that generic label ("cellular
   telephone", "pop bottle"...) to one of the 25 specific items in the
   campus catalog and returns exactly how to dispose of it — bin, hazard
   level, whether it's reusable, and where the nearest collection point is.
2. **Catalog** — browse/search/filter all 200 records from the dataset
   (category, hazard level, recyclability, disposal method, instructions).
3. **Dashboard** — live stats computed from the database: item counts by
   category and hazard level, e-waste vs. recyclable totals, and a log of
   every real scan performed (this is the "Assess Impact" phase of the
   project roadmap in the internship deck).

## Architecture

```
EcoSortAI/
├── backend/
│   ├── app.py            Flask REST API
│   ├── database.py       builds SQLite DB from the CSV dataset
│   ├── cv_mapping.py      CV-label → catalog-item lookup table
│   ├── requirements.txt
│   └── eco_sort.db        (created on first run)
├── data/
│   └── Eco-Sort-Cleaned.csv   the original 1M1B dataset (200 rows)
└── frontend/
    ├── index.html
    ├── style.css
    ├── config.js          points the frontend at your backend URL
    └── app.js             camera/CV pipeline + catalog + dashboard logic
```

- **Database**: SQLite, seeded once from `data/Eco-Sort-Cleaned.csv` into an
  `items` table. A second `scan_logs` table records every scan (source,
  predicted label, confidence, matched item, timestamp) so the dashboard
  reflects real usage, not just static catalog counts.
- **Backend**: Flask, plain `sqlite3` (no ORM needed at this size). Routes
  for listing/filtering/searching items, category and location lists,
  aggregate stats, and the `/api/lookup` endpoint that the scan feature
  calls.
- **Computer vision**: MobileNet v2 (via TensorFlow.js), loaded and run
  **client-side** — no GPU server needed, no images ever have to leave the
  browser. It classifies against the standard 1000 ImageNet classes;
  `cv_mapping.py` translates those generic labels into the 25 specific
  items that exist in the campus dataset (e.g. `"pop bottle"` →
  `Plastic Bottle`, `"cellular telephone"` → `Mobile`). If nothing matches
  confidently, the UI says so honestly rather than guessing.
- **Frontend**: plain HTML/CSS/JS (no build step) so it's easy to run
  anywhere — open the file, or serve it, and it talks to the Flask API.

## Running it

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python database.py     # builds & seeds eco_sort.db (only needed once)
python app.py           # serves the API on http://localhost:5000
```

### 2. Frontend

Just serve the `frontend/` folder as static files (opening `index.html`
directly also works in most browsers, but a local server avoids camera
permission quirks):

```bash
cd frontend
python -m http.server 8080
```

Then open `http://localhost:8080` in your browser. If your backend runs
somewhere other than `localhost:5000`, update `API_BASE` in
`frontend/config.js`.

## Mapping to the internship phases

| Phase | What this project delivers |
|---|---|
| **Foundations** | Dataset cleaning & understanding (already done — `Eco-Sort-Cleaned.csv`) |
| **Analysis** | The catalog + dashboard views: category, hazard, and recyclability breakdowns |
| **Application** | The AI-enabled solution: CV-based item recognition + rule-based disposal lookup, backed by a real database and API |
| **Impact** | The dashboard's scan log — a live record of real usage you can screenshot for your demo/showcase |

## Ideas to extend for your final submission

- Add a **QR code per campus bin** that opens the Scan view pre-filtered to
  that location.
- Fine-tune a small custom image classifier on your own photos of the 25
  items instead of relying solely on generic ImageNet labels — would make
  scan accuracy much higher for items like "Remote Control" that MobileNet
  doesn't have a clean class for.
- Add a "report a bin" feature that writes into `scan_logs` with a
  `flagged` reason, for your impact-assessment section.
- Deploy the backend (e.g. Render/Railway) and the frontend (e.g. GitHub
  Pages) so your demo-day link works from any phone.
