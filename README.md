# Trolley Tube Bend Tracker

A Flask web application for tracking trolley tube bending operations, designed for deployment on Vercel.

## Features

- **Add Bend Records** — Log tube bending jobs with material, diameter, angle, radius, trolley model, operator, and status
- **Edit Records** — Update any existing bend record with a dedicated edit page
- **Dashboard Stats** — View total bends, pass/fail/pending counts, and pass rate at a glance
- **Failure Breakdown** — Visual breakdown of failure reasons when records fail
- **Status Tracking** — Mark bends as Pass, Fail, or Pending
- **Fail Reason Codes** — When a bend fails, select from standardized reason codes: Wrinkling, Flattening, Springback, Cracking, Ovality, Galling, Incorrect Angle, Incorrect Radius, Material Defect, Tooling Issue, or Other
- **Search & Filter** — Search by job number, operator, or trolley model; filter by status, material, and date range
- **CSV Export** — Download all records as a CSV file for reporting
- **Responsive Design** — Works on desktop, tablet, and mobile
- **REST API** — Access bend data via `/api/bends` and `/api/bends/<id>`
- **Delete Records** — Remove entries with confirmation

## Project Structure

```
TrolleyBendTracker/
├── api/
│   └── index.py          # Flask application entry point
├── templates/
│   └── index.html        # Main UI template
├── static/
│   └── style.css         # Stylesheet
├── instance/
│   └── bends.db          # SQLite database (created at runtime)
├── vercel.json           # Vercel deployment config
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   python api/index.py
   ```

3. **Open in browser:**
   Navigate to `http://localhost:5000`

## Deploy to Vercel

### Option 1: Vercel CLI

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   vercel
   ```

### Option 2: GitHub Integration

1. Push this repository to GitHub
2. Import the project on [vercel.com](https://vercel.com)
3. Vercel will auto-detect the Flask app and deploy it

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main dashboard with search & filters |
| POST | `/add` | Add a new bend record |
| GET/POST | `/edit/<id>` | Edit an existing bend record |
| GET | `/delete/<id>` | Delete a bend record |
| GET | `/export` | Download all records as CSV |
| GET | `/api/bends` | Get all bends as JSON |
| GET | `/api/bends/<id>` | Get a specific bend as JSON |

## Data Model

Each bend record contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Auto-incrementing ID |
| `date` | String | Date of the bend (YYYY-MM-DD) |
| `job_number` | String | Job identifier |
| `tube_material` | String | Material type (Steel, Aluminum, etc.) |
| `tube_diameter` | String | Tube diameter in mm |
| `bend_angle` | String | Bend angle in degrees |
| `bend_radius` | String | Bend radius in mm |
| `trolley_model` | String | Trolley model used |
| `operator` | String | Operator name |
| `status` | String | Pass / Fail / Pending |
| `fail_reason` | String | Reason for failure (required when status is Fail) |
| `notes` | String | Additional notes |
| `created_at` | String | ISO timestamp |

## Notes

- Data is stored in an **SQLite database** (`instance/bends.db`). On Vercel's serverless platform, the filesystem is ephemeral so data will reset on each deployment/cold start. For persistent storage in production, set the `DATABASE_URL` environment variable to a PostgreSQL connection string (e.g., from Vercel Postgres, Supabase, or Railway).
- The secret key can be set via the `SECRET_KEY` environment variable on Vercel.
- To use PostgreSQL instead of SQLite, set `DATABASE_URL=postgresql://user:pass@host/dbname` in your environment variables.
