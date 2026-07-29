import os
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models import db, User, Favorite, SearchHistory

# Load secret values (API key, search engine ID, secret key) from .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scholarships.db'

# Connect our database models (from models.py) to this app
db.init_app(app)

app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutes
cache = Cache(app)

limiter = Limiter(get_remote_address, app=app, default_limits=[])

# Set up Flask-Login to manage who is logged in
login_manager = LoginManager()
login_manager.login_view = 'login'  # send visitors here if they're not logged in
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- AUTH ROUTES ----------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please fill in both username and password.')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('That username is already taken. Please choose another.')
            return redirect(url_for('register'))

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Incorrect username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---------- PAGES ----------

@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/favorites')
@login_required
def favorites():
    saved = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.saved_at.desc()).all()
    return render_template('favorites.html', favorites=saved)


@app.route('/history')
@login_required
def history():
    searches = SearchHistory.query.filter_by(user_id=current_user.id).order_by(SearchHistory.searched_at.desc()).all()
    return render_template('history.html', searches=searches)


# ---------- SEARCH API (calls Adzuna + Remotive) ----------

@app.route('/api/search', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def api_search():
    data = request.get_json()
    keyword = data.get('keyword', '').strip()
    location = data.get('location', '').strip()

    if not keyword or not location:
        return jsonify({'error': 'Please fill in a keyword and choose a location.'}), 400

    cache_key = f"search:{keyword.lower()}:{location.lower()}"
    results = cache.get(cache_key)

    if results is not None:
        print('CACHE HIT for:', cache_key)
    else:
        print('CACHE MISS for:', cache_key)
        try:
            if location.lower() == 'remote':
                results = search_remotive(keyword)
            else:
                results = search_adzuna(keyword, location)
        except requests.exceptions.RequestException as e:
            print('JOB SEARCH ERROR:', e)
            if e.response is not None:
                print('JOB SEARCH RESPONSE BODY:', e.response.text)
            return jsonify({'error': 'Could not reach the job search service. Please try again later.'}), 502

        cache.set(cache_key, results, timeout=300)

    if not results:
        return jsonify({'results': [], 'message': 'No jobs found. Try a different keyword or location.'})

    # Log this search into the user's history
    new_search = SearchHistory(user_id=current_user.id, keyword=keyword, location=location)
    db.session.add(new_search)
    db.session.commit()

    return jsonify({'results': results})


def search_adzuna(keyword, country_code):
    app_id = os.getenv('ADZUNA_APP_ID')
    app_key = os.getenv('ADZUNA_APP_KEY')

    response = requests.get(
        f'https://api.adzuna.com/v1/api/jobs/{country_code}/search/1',
        params={
            'app_id': app_id,
            'app_key': app_key,
            'what': keyword,
            'results_per_page': 15,
            'content-type': 'application/json'
        },
        timeout=10
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for job in data.get('results', []):
        company = job.get('company', {}).get('display_name', 'Unknown company')
        job_location = job.get('location', {}).get('display_name', '')
        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')

        salary_text = ''
        if salary_min and salary_max:
            salary_text = f" | Salary: {int(salary_min):,} - {int(salary_max):,}"

        description = job.get('description', '')[:200]
        snippet = f"{company} | {job_location}{salary_text}\n{description}"

        results.append({
            'title': job.get('title', ''),
            'link': job.get('redirect_url', ''),
            'snippet': snippet,
            'source_site': company
        })

    return results


def search_remotive(keyword):
    response = requests.get(
        'https://remotive.com/api/remote-jobs',
        params={'search': keyword},
        timeout=10
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for job in data.get('jobs', [])[:15]:
        company = job.get('company_name', 'Unknown company')
        job_location = job.get('candidate_required_location', 'Remote')
        salary = job.get('salary', '')

        salary_text = f" | Salary: {salary}" if salary else ''
        snippet = f"{company} | {job_location}{salary_text}\n{job.get('job_type', '')}"

        results.append({
            'title': job.get('title', ''),
            'link': job.get('url', ''),
            'snippet': snippet,
            'source_site': company
        })

    return results

# ---------- FAVORITES API ----------

@app.route('/api/favorites', methods=['POST'])
@login_required
def add_favorite():
    data = request.get_json()

    new_favorite = Favorite(
        user_id=current_user.id,
        title=data.get('title', ''),
        link=data.get('link', ''),
        snippet=data.get('snippet', ''),
        source_site=data.get('source_site', '')
    )
    db.session.add(new_favorite)
    db.session.commit()

    return jsonify({'message': 'Saved to favorites!'})


@app.route('/api/favorites/<int:favorite_id>', methods=['DELETE'])
@login_required
def delete_favorite(favorite_id):
    favorite = Favorite.query.get(favorite_id)

    if not favorite or favorite.user_id != current_user.id:
        return jsonify({'error': 'Favorite not found.'}), 404

    db.session.delete(favorite)
    db.session.commit()

    return jsonify({'message': 'Removed from favorites.'})


# ---------- START THE APP ----------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # creates scholarships.db and its tables if they don't exist yet
    app.run(debug=True)
