# RESQ AI

**Intelligent Fire Detection, Risk Prediction & Rescue Response Coordination**

RESQ AI is an AI-powered emergency response dashboard that works like a fire incident command center. It monitors a building in real time, predicts fire risk, and helps coordinate rescue operations from a single screen.

## Features

- **Fire detection:** live sensor and CCTV signals are used to detect fire and smoke.
- **Risk prediction:** a risk engine scores each floor and zone and shows a heatmap.
- **3D building view:** floor-by-floor view of the building with occupants, fire/smoke, sensors and CCTV.
- **Map layers:** toggle occupants, fire/smoke, heatmap, rescue and blocked routes, sensors and CCTV on or off.
- **Rescue coordination:** safe and blocked evacuation routes, and a dashboard to track incidents and response.

## Tech Stack

| Part     | Technology                                  |
| -------- | ------------------------------------------- |
| Frontend | React, Vite                                 |
| Backend  | Python, FastAPI, SQLAlchemy                 |
| Database | SQLite (seeded with sample datasets)        |
| Server   | Uvicorn                                     |

## Project Structure

```
RESQ_AI/
├── frontend/        # React + Vite app
├── backend/         # FastAPI app, risk engine, database models
├── package.json
└── README.md
```

## Getting Started

### Prerequisites

- Node.js 18 or higher
- Python 3.10 or higher

### 1. Clone the repository

```bash
git clone https://github.com/muskanpadoti04-beep/resq-ai-fullstack.git
cd resq-ai-fullstack/RESQ_AI
```

### 2. Run the backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at `http://localhost:8000` and the docs are at `http://localhost:8000/docs`.

### 3. Run the frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

## Environment Variables

If the project needs secrets, create a `.env` file in the backend folder. Never commit this file.

```
# example
API_KEY=your_key_here
```

## Notes

- This is a software-only prototype. Sensor, CCTV and occupant data are simulated from seeded datasets.
- Folder names and run commands above may differ slightly from your setup. Adjust them if needed.

## Author

Muskan Padoti
