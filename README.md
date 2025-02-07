# jobs_manager

A Django-based jobs/quotes/work management system customized for **Morris Sheetmetal** needs. Inspired by [django-timepiece](https://github.com/lincolnloop/django-timepiece), with added features such as:

- **CRM** with projects and businesses  
- **User dashboards** with budgeted hours based on project contracts  
- **Time sheets** (daily, weekly, monthly summaries)  
- **Approved and invoiced** time sheet workflows  
- **Monthly payroll** reporting (overtime, paid leave, vacation)  
- **Project invoicing** with hourly summaries  

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation (Local)](#installation-local)
- [Settings Module](#settings-module)
- [Database Setup](#database-setup)
- [Environment Variables](#environment-variables)
- [AWS Deployment Notes](#aws-deployment-notes)
- [Running the App](#running-the-app)
- [Fixtures & Xero Sync](#fixtures--xero-sync)
- [License](#license)

---

## Features

1. **CRM**: Tracks companies, projects, and quotes.  
2. **Time Sheets**: Enter, manage, and invoice hours.  
3. **Dashboards**: Visibility into each project’s budget.  
4. **Payroll**: Monthly summaries with overtime/leave.
5. **Integrations**:
   - **Dropbox**: Files are saved to a local Dropbox folder and synced via the Dropbox desktop app
   - **Xero**: Integration for invoicing/payroll

---

## Requirements

- **Python 3.12+**  
- **[Poetry](https://python-poetry.org/)** (manages Python dependencies)  
- **Node.js + npm** (manages JavaScript dependencies, even if lightly used)  
- **MariaDB 11.5.2** (locally)

---

## Installation (Local)

Follow these steps for a **local development** environment:

1. **Clone the repo**:
   ```bash
   git clone https://github.com/corrin/jobs_manager.git
   cd jobs_manager
   ```
2. **Create a virtual environment**:
   ```bash
   pip install virtualenv
   python -m virtualenv venv
   ```
3. **Install Python dependencies**:
   ```bash
   poetry install
   ```
4. **Install JS dependencies**:
   ```bash
   npm install
   ```
5. **Set up the database** (see [Database Setup](#database-setup)).

6. **Configure environment variables** (see [Environment Variables](#environment-variables)).

7. Activate `venv`:
    
    ```bash
    venv\Scripts\activate # or "source venv\bin\activate" in Linux 
    ```
    
4. **Run migrations**:
    
    ```bash
    python manage.py migrate
    ```
    
5. **Start the development server**:
    
    ```bash
    # In VSCode, use the "Django" launch configuration for debugging
    # Or run directly in terminal:
    poetry run python manage.py runserver
    ```
    
    Then open http://127.0.0.1:8000 in your browser.

6. **For Xero integration, run ngrok in a separate terminal**:
    
    ```bash
    # In a new terminal:
    python manage.py launch_ngrok
    ```
    
    This tries to make your local server available at msm-workflow.ngrok-free.app for Xero OAuth callbacks.
    If that domain is unavailable, it will fall back to an automatically assigned domain (e.g., measured-enormously-man.ngrok-free.app).

---

## Settings Module

This project uses a **modular settings** approach under the `settings/` directory, with files like:

- `base.py` - Base settings shared across environments
- `local.py` - Development settings with debug tools
- `production_like.py` - Settings for Xero/Dropbox integration with additional security

By default, Django loads `settings/__init__.py`, which imports either `local` or `production_like` depending on the environment variable `DJANGO_ENV`. For example:

```python
# settings/__init__.py
import os

ENVIRONMENT = os.getenv('DJANGO_ENV', 'local')

if ENVIRONMENT == 'production_like':
    from .production_like import *  # For Xero/Dropbox integration
else:
    from .local import *  # Default development settings
```

- **Local development**: `DJANGO_ENV=local` (default)
- **Integration mode**: `DJANGO_ENV=production_like` (requires Redis/Celery)

Note: production_like.py enables Xero/Dropbox integration but requires additional services:
- Redis for caching
- Celery for background tasks
- Stricter security settings

---

## Database Setup

Our application expects a **MariaDB 11.5.2** (or MySQL-compatible) database.

### Local MariaDB Setup

1. Install MariaDB locally (e.g., `sudo apt install mariadb-server` on Ubuntu).
2. Create a database and user:
    
    ```sql
    CREATE DATABASE msm_workflow;
    CREATE USER 'msm_user'@'localhost' IDENTIFIED BY 'your-password';
    GRANT ALL PRIVILEGES ON msm_workflow.* TO 'msm_user'@'localhost';
    FLUSH PRIVILEGES;
    ```
    
3. Update your environment variables (`DB_PASSWORD`, etc.) accordingly.

---

## Environment Variables

Create a file named **`.env`** in the project root (or configure them in your environment). Below are the commonly used vars (check .env.example for a full list).

```bash
DEBUG=True
SECRET_KEY=your-django-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,msm-workflow.ngrok-free.app

# Ngrok configuration (for Xero integration)
NGROK_DOMAIN=msm-workflow.ngrok-free.app

# Database configuration
MSM_DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_PORT=your-db-port

```

> Note: You can customize or add others as needed (DJANGO_ENV=production_like, etc.).
> 

---

## Running the App

1. **Activate virtual environment**:
    
    ```bash
    venv\Scripts\activate # or "source venv\bin\activate" in Linux
    ```
    
2. **Apply migrations**:
    
    ```bash
    python manage.py migrate
    ```
    
3. **Collect static files**:
    
    ```bash
    python manage.py collectstatic
    ```
    
4. **Start the server** (development):
    
    ```bash
    python manage.py runserver
    ```
    
5. **Or run with Gunicorn** (production-like):
    
    ```bash
    gunicorn --bind 0.0.0.0:8000 jobs_manager.wsgi
    ```
    

---

## Fixtures & Xero Sync

- **Fixtures**: The project have fixtures to load initial data (e.g., example clients, test data). Install them by:
    
    ```bash
    python manage.py loaddata fixture_file.json
    
    ```
    
- **Xero Sync**: After the app is running, click the **“Refresh Xero data”** button (in the admin or custom view) to fetch data from Xero (clients, invoices, etc.).

---

## License

This project is proprietary to **Morris Sheetmetal**. For inquiries or usage permissions, contact the repository maintainer.

---

**Enjoy your time managing jobs in `jobs_manager`!**

For any questions or issues, please open an issue on GitHub or reach out to the team.
