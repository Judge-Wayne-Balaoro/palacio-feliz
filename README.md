# Palacio Feliz Full-Stack (Flask + MySQL)

This package combines your Flask backend with your uploaded customer page, admin login page, and admin dashboard.

## What was fixed
- Added page routes:
  - `/` → customer page
  - `/login` → admin login page
  - `/admin` → admin dashboard
- Moved frontend files into Flask `templates/` and `static/`
- Updated frontend scripts to use relative API endpoints (`/api/...`)
- Connected customer booking form to the Flask booking API
- Connected admin dashboard sections to live backend APIs
- Updated `.env.example`
- Updated `requirements.txt` for modern Pillow and added `cryptography`

## Setup
1. Create the database in MySQL:
   ```sql
   CREATE DATABASE palacio_feliz;
   ```
2. Copy the environment file:
   ```powershell
   copy .env.example .env
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Seed the database:
   ```powershell
   python seed.py
   ```
5. Run the app:
   ```powershell
   python run.py
   ```

## URLs
- Customer page: `http://127.0.0.1:5000/`
- Admin login: `http://127.0.0.1:5000/login`
- Admin dashboard: `http://127.0.0.1:5000/admin`

## Default admin account
- Username: `admin`
- Password: `Admin@1234`

## Note about images/videos
Your uploaded package did not include the original `Assets/` files referenced by the HTML. The pages and routing are wired up, but you may still want to add your real images/videos into `static/assets/`.
