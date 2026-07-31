 Job & Internship Finder


A web application that helps students and job seekers search for real internships, graduate jobs, and remote work opportunities — built for the "Playing Around with APIs" assignment.


Why this app?


Finding relevant internships and remote jobs across multiple job boards is tedious and scattered. This app pulls real, live job listings from two job-search APIs into one place, lets users filter and sort results, and lets logged-in users save favorites and revisit their search history, solving a genuine, everyday problem for students rather than being a novelty app.


Features


- Search: for jobs/internships by keyword and location (19 supported countries, or "Remote")
- Two live external APIs combined: country-based search via Adzuna, remote-only search via Remotive
- Sort and filter: results by company, right in the browser, with no extra server calls
- User accounts: (register/login) with securely hashed passwords (Werkzeug `pbkdf2:sha256`)
- Save favorites and view search history both stored per-user in a server-side database
- Error handling: for missing input, unreachable APIs, and zero results — always a clear message, never a crash
- Response caching(Flask-Caching): identical searches within 5 minutes are served instantly without re-calling the external APIs
- Rate limiting(Flask-Limiter: caps searches by client IP per minute to protect API quota from abuse 


APIs Used (credit)


- [Adzuna API](https://developer.adzuna.com/): job listings by country, with salary and company data. Free tier, requires a free `app_id` + `app_key`.
- [Remotive API](https://remotive.com/remote-jobs/api): dedicated remote-jobs board. Free, no API key required.


Both APIs' documentation, terms, and attribution requirements were reviewed before use.


Tech Stack


-Backend:Python, Flask (https://flask.palletsprojects.com/), Flask-SQLAlchemy (https://flask-sqlalchemy.palletsprojects.com/), Flask-Login (https://flask-login.readthedocs.io/), Flask-Caching (https://flask-caching.readthedocs.io/), Flask-Limiter (https://flask-limiter.readthedocs.io/)

-Database:SQLite

-Frontend:HTML, CSS, vanilla JavaScript (fetch API)

-Deployment:Gunicorn (WSGI server) + Nginx (reverse proxy) + systemd (process management)

-Load balancing:HAProxy with sticky sessions (`balance source`)


Running Locally


1. Clone this repository and `cd` into it.
2. Create and activate a virtual environment:
  ```bash
  python3 -m venv venv
  source venv/bin/activate   # Windows: venv\Scripts\activate
```

3. Install dependencies:pip install -r requirements.txt

4. Create a .env file in the project root (never committed — see .gitignore):

  ADZUNA_APP_ID=your_adzuna_app_id
  
  ADZUNA_APP_KEY=your_adzuna_app_key
  
  SECRET_KEY=any_long_random_string

5. Get free Adzuna credentials at https://developer.adzuna.com/signup.
6. Run the app:python app.py
7. Open http://127.0.0.1:5000, register an account, and start searching.
   
Deployment (Part Two)


The app is deployed on two identical web servers (Web01, Web02) behind a load balancer (Lb01).
On each web server:

1.Cloned this repository into /var/www/jobfinder.
2. Created a Python virtual environment and installed requirements.txt.
3. Created a .env file with the same Adzuna credentials and the same SECRET_KEY on both servers.
4. Created the database tables with a one-off command (db.create_all() via the app context), since Gunicorn doesn't trigger the app's if name == 'main' block.
5. Ran Gunicorn as a systemd service (jobfinder.service) bound to 127.0.0.1:8000, so it restarts automatically on crash or reboot.
6. Configured Nginx as a reverse proxy, forwarding all traffic on port 80 to Gunicorn on port 8000.
7. I also 


On the load balancer (Lb01):

Traffic is routed through HAProxy, running on `lb-01`, which load-balances requests between `web-01` and `web-02`. HAProxy listens on both port 80 (HTTP) and port 443 (HTTPS) and forwards requests to the backend servers regardless of which domain (root or `www`) was used to reach it. It was configured with balance source (sticky sessions based on client IP) rather than plain round-robin.


Why sticky sessions?


Each web server keeps its own local SQLite database. With plain round-robin balancing, a single user's requests could bounce between servers mid-session for example: registering an account on Web01, then getting logged out because Web02 has no record of that account. balance source ensures a given visitor is consistently routed to the same backend server for the life of their session, while different visitors are still distributed across both servers. This keeps the app fully functional without requiring a separate shared database server.

Domain & HTTPS setup

This project is deployed and accessible via a custom domain:

Live URL: https://ericas.tech (also accessible via https://www.ericas.tech)

DNS Configuration
My domain `ericas.tech` is registered through .tech domains. DNS is configured with A records pointing both the root domain (`@`) and the `www` subdomain to the public IP address of the load balancer (`lb-01`), which distributes incoming traffic across two backend web servers (`web-01` and `web-02`).

SSL & HTTPS
The site is secured with a free SSL/TLS certificate issued by Let's Encrypt, covering both `ericas.tech` and `www.ericas.tech`. The certificate is installed on the load balancer and is set to auto-renew, with a deployment hook that automatically updates HAProxy's configuration whenever the certificate is renewed.


Bonus Features Implemented

1.User authentication: full register/login/logout system with hashed passwords

2.Response caching : Flask-Caching avoids redundant external API calls for repeated searches

3. Rate limiting : Flask-Limiter caps search requests per client IP per minute(10requests/min)

Testing & Verification

Each web server tested independently first: before touching the load balancer, Web01 and Web02 were each tested directly via their public IPs (curl -I and a browser check), confirming both served the login page correctly on their own.

Load balancer tested end-to-end: accessed the app via Lb01's public IP (http://44.204.238.87/) in a browser and confirmed the full app : login, search, favorites, history. It works identically through the load balancer as it does hitting a server directly.

Confirmed which backend handles a request: ran curl -I http://44.204.238.87/ and checked the X-Served-By response header (added by Nginx on each server), showing which of Web01/Web02 actually served that request.

Traffic distribution: HAProxy's backend web_servers block uses check on both servers, so HAProxy continuously health-monitors each one and only routes to servers confirmed to be up. With balance source (sticky sessions), a single client is consistently routed to the same backend for their whole session, it is verified by repeated curl requests from the same machine always returning the same X-Served-By value, while different clients (different source IPs) are distributed across both Web01 and Web02.


Challenges & How They Were Solved

1. Initial API choice (ScholarshipAPI) had a broken signup flow with no way to get a key which led to a different app concept (Job & Internship Finder) built around Adzuna + Remotive instead.
2. Google Cloud org policy blocked billing/API access on a school-managed Google account during an earlier iteration, resolved by using APIs (Adzuna, Remotive) that don't require Google Cloud at all.
3. SQLite is per-server, not shared; it was addressed architecturally with HAProxy sticky sessions (see above) instead of introducing a separate database server, keeping the deployment simpler and more reliable.
4. Missing dependencies after a code update — the first deploy of a new feature caused a 502 error because new Python packages (Flask-Caching, Flask-Limiter) were added to requirements.txt locally but not yet installed on the servers; fixed by running pip install -r requirements.txt on each server.


Live Demo

Deployed app (via load balancer): http://44.204.238.87/ 

Domain setup with SSL: https://ericas.tech or https://www.ericas.tech

Demo video: [link to my video](https://youtu.be/nDGCGG-1dUA)


Credentials for Grading

API keys and a grader login account are provided separately in the assignment submission comments, not in this public repository, to avoid exposing secrets.
