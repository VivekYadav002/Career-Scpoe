from flask import Flask, render_template, request, Response, url_for, redirect, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
import csv, os, re, io, sqlite3
from collections import Counter
from contextlib import closing

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, 'data')
INSTANCE_DIR = os.path.join(BASE, 'instance')
USERS_DB = os.path.join(INSTANCE_DIR, 'accounts.sqlite3')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('CAREERSCOPE_SECRET_KEY', 'careerscope-local-development-key')

def initialize_user_db():
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    with closing(sqlite3.connect(USERS_DB)) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        db.commit()

initialize_user_db()

CITIES = ['Ahmedabad', 'Bangalore', 'Chennai', 'Gurugram', 'Hyderabad', 'Indore', 'Jaipur', 'Mumbai', 'Noida', 'Pune']

def parse_other(value):
    parts = [x.strip() for x in (value or '').split(',') if x.strip()]
    industry = parts[0] if parts else 'Not specified'
    employees = next((p for p in parts if 'employee' in p.lower() or 'lakh+' in p.lower()), 'Not specified')
    company_type = next((p for p in parts if p.lower() in {'public','private','partnership','government'} or 'fortune' in p.lower() or 'forbes' in p.lower()), 'Not specified')
    age = next((p for p in parts if re.search(r'\d+\s+years? old', p.lower())), 'Not specified')
    location = next((p for p in parts if re.search(r'\+\d+ more', p.lower()) or '/' in p or p.lower() in {c.lower() for c in CITIES}), 'Not specified')
    return industry, employees, company_type, age, location

def load_companies():
    rows=[]
    if not os.path.isdir(DATA_DIR): return rows
    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.lower().endswith('.csv'): continue
        city=os.path.splitext(filename)[0].replace('_',' ').title()
        try:
            with open(os.path.join(DATA_DIR,filename),newline='',encoding='utf-8-sig',errors='replace') as f:
                for row in csv.DictReader(f):
                    name=(row.get('company_name') or '').strip()
                    if not name: continue
                    raw=(row.get('other_data') or '').strip()
                    industry,employees,ctype,age,location=parse_other(raw)
                    try: rating=float(row.get('company_rating') or 0)
                    except (ValueError,TypeError): rating=0
                    rows.append({'id':len(rows)+1,'company_name':name,'rating':rating,'industry':industry,'employees':employees,'company_type':ctype,'age':age,'location':location,'city':city,'other_data':raw})
        except (OSError,csv.Error): pass
    return rows

COMPANIES=load_companies()
CITIES_AVAILABLE=sorted({r['city'] for r in COMPANIES})
INDUSTRIES=sorted({r['industry'] for r in COMPANIES})

def filtered_rows(args):
    rows=COMPANIES
    q=args.get('q','').strip().lower()
    city=args.get('city','').strip()
    industry=args.get('industry','').strip()
    min_rating=args.get('min_rating','').strip()
    sort=args.get('sort','rating')
    if q: rows=[r for r in rows if q in r['company_name'].lower() or q in r['industry'].lower() or q in r['location'].lower()]
    if city: rows=[r for r in rows if r['city']==city]
    if industry: rows=[r for r in rows if r['industry']==industry]
    if min_rating:
        try: rows=[r for r in rows if r['rating']>=float(min_rating)]
        except ValueError: pass
    if sort=='name': rows=sorted(rows,key=lambda r:r['company_name'].lower())
    elif sort=='rating_low': rows=sorted(rows,key=lambda r:r['rating'])
    else: rows=sorted(rows,key=lambda r:r['rating'],reverse=True)
    return rows

def analytics():
    rated=[r for r in COMPANIES if r['rating']>0]
    return {
      'total':len(COMPANIES), 'unique':len({r['company_name'].lower() for r in COMPANIES}),
      'city_total':len({r['city'] for r in COMPANIES}), 'industry_total':len({r['industry'] for r in COMPANIES}),
      'avg':round(sum(r['rating'] for r in rated)/len(rated),2) if rated else 0,
      'city_counts':Counter(r['city'] for r in COMPANIES).most_common(8),
      'industry_counts':Counter(r['industry'] for r in COMPANIES).most_common(8),
      'rating_bands':Counter('4.0–5.0' if r['rating']>=4 else '3.0–3.9' if r['rating']>=3 else '2.0–2.9' if r['rating']>=2 else '0–1.9' for r in rated).most_common()
    }

@app.route('/')
def home():
    all_rows=filtered_rows(request.args)
    per_page=20
    try: page=max(1,int(request.args.get('page','1')))
    except ValueError: page=1
    pages=max(1,(len(all_rows)+per_page-1)//per_page)
    page=min(page,pages)
    rows=all_rows[(page-1)*per_page:page*per_page]
    return render_template('index.html', companies=rows, total_filtered=len(all_rows), page=page, pages=pages,
      cities=CITIES_AVAILABLE, industries=INDUSTRIES, stats=analytics(), q=request.args.get('q',''),
      selected_city=request.args.get('city',''), selected_industry=request.args.get('industry',''),
      min_rating=request.args.get('min_rating',''), sort=request.args.get('sort','rating'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('home'))
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirmation = request.form.get('confirm_password', '')
        if not name or len(name) > 80:
            flash('Enter a name with no more than 80 characters.', 'error')
        elif not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
            flash('Enter a valid email address.', 'error')
        elif len(password) < 8:
            flash('Your password must be at least 8 characters long.', 'error')
        elif password != confirmation:
            flash('The passwords do not match.', 'error')
        else:
            try:
                with closing(sqlite3.connect(USERS_DB)) as db:
                    cursor = db.execute(
                        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                        (name, email, generate_password_hash(password))
                    )
                    user_id = cursor.lastrowid
                    db.commit()
            except sqlite3.IntegrityError:
                flash('An account with that email already exists. Log in instead.', 'error')
            else:
                session.clear()
                session['user_id'] = user_id
                session['user_name'] = name
                flash('Your account has been created.', 'success')
                return redirect(url_for('home'))
    return render_template('register.html', name=name, email=email)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('home'))
    email = request.form.get('email', '').strip().lower()
    if request.method == 'POST':
        password = request.form.get('password', '')
        with closing(sqlite3.connect(USERS_DB)) as db:
            db.row_factory = sqlite3.Row
            user = db.execute(
                'SELECT id, name, password_hash FROM users WHERE email = ?', (email,)
            ).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('You are signed in.', 'success')
            return redirect(url_for('home'))
        flash('Email or password is incorrect.', 'error')
    return render_template('login.html', email=email)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out.', 'success')
    return redirect(url_for('home'))

@app.route('/company/<int:company_id>')
def company_detail(company_id):
    item=next((r for r in COMPANIES if r['id']==company_id),None)
    if item is None: return render_template('detail.html',company=None),404
    return render_template('detail.html',company=item)

@app.route('/export')
def export_csv():
    rows=filtered_rows(request.args)
    output=io.StringIO(newline='')
    fields=['company_name','rating','industry','employees','company_type','age','location','city']
    writer=csv.DictWriter(output,fieldnames=fields,extrasaction='ignore')
    writer.writeheader(); writer.writerows(rows)
    return Response('\ufeff'+output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=careerscope_companies.csv'})

@app.route('/health')
def health(): return {'status':'ok','records':len(COMPANIES)}

if __name__=='__main__':
    print(f'CareerScope loaded {len(COMPANIES):,} company records')
    app.run(debug=False,host='127.0.0.1',port=5000)
