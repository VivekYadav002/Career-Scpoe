# CareerScope — Python-only College Project

**Title:** CareerScope: A Data-Driven Company Insights and Career Discovery Platform

CareerScope is a server-rendered company directory and analytics website built using Python, Flask, CSV, HTML, and CSS. The frontend contains **no JavaScript**. Search, filters, sorting, pagination, company detail pages, and CSV export are handled by Flask routes and standard HTML forms.

## Features
- Search company names, industries, and locations
- Filter by city, industry, and minimum rating
- Sort by highest rating, lowest rating, or company name
- Server-rendered company profile pages
- Summary metrics and analytics bars calculated using Python
- Export filtered results as CSV
- Register and log in with locally stored accounts
- Passwords are stored as secure hashes in a SQLite database
- Health endpoint at `/health`
- Uses the 10 city-wise CSV files included in `data/`

## Requirements
- Python 3.10 or newer
- Flask

## Windows setup
1. Extract the project ZIP.
2. Open PowerShell in the `CareerScope_College_Project` folder.
3. Install dependencies:
   ```powershell
   py -m pip install -r requirements.txt
   ```
4. Start the app:
   ```powershell
   py app.py
   ```
5. Open `http://127.0.0.1:5000` in Chrome.

## Project structure
```
CareerScope_College_Project/
├── app.py
├── requirements.txt
├── README.md
├── data/                  # 10 city-wise CSV files
├── templates/
│   ├── index.html
│   ├── detail.html
│   ├── login.html
│   └── register.html
└── static/
    └── style.css
   └── auth.css
```

## Main routes
- `/` — directory, filters, pagination, analytics
- `/company/<id>` — server-rendered company profile
- `/register` — create an account
- `/login` — sign in
- `/logout` — sign out
- `/export` — export filtered results to CSV
- `/health` — status and loaded record count

## Academic overview
**Problem statement:** Company information is distributed across multiple city-wise data files, making it difficult to search and compare consistently.

**Objectives:** Consolidate CSV records at runtime, make company data searchable, filter and sort listings, calculate descriptive statistics, and export selected records.

**Methodology:** Python's built-in `csv` and `sqlite3` modules load records and store accounts; Werkzeug hashes passwords; Flask processes requests and sessions; Jinja templates render HTML; CSS provides responsive presentation. No client-side JavaScript is used.

**Limitations:** City is inferred from the source filename. Some fields are extracted heuristically from `other_data`. Repeated companies across cities can increase record counts. Ratings and company details are displayed as supplied and are not independently verified. The dataset does not contain verified employee reviews, salaries, or live job vacancies.

**Future scope:** Add moderated employee-submitted reviews, salary datasets, and a recommendation model after obtaining suitable data.
