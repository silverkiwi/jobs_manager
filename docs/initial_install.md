# Initial Installation Guide

## Requirements

- **Python 3.12+**  
- **[Poetry](https://python-poetry.org/)** (manages Python dependencies)  
- **Node.js + npm** (manages JavaScript dependencies)  
- **MariaDB 11.5.2** (locally)

## Installation Steps

### 1. Clone and Install Dependencies

```bash
git clone https://github.com/corrin/jobs_manager.git
cd jobs_manager
poetry install
npm install
```

### 2. Database Setup

Our application expects a **MariaDB 11.5.2** (or MySQL-compatible) database.

1. Install MariaDB locally (e.g., `sudo apt install mariadb-server` on Ubuntu).
2. Create a database and user:
    ```sql
    CREATE DATABASE msm_workflow;
    CREATE USER 'msm_user'@'localhost' IDENTIFIED BY 'your-password';
    GRANT ALL PRIVILEGES ON msm_workflow.* TO 'msm_user'@'localhost';
    FLUSH PRIVILEGES;
    ```

### 3. Environment Setup

1. Copy `.env.example` to `.env` in the project root
2. Update the values according to your environment (the example file includes explanatory comments)
3. Make sure to update the database credentials to match what you created in step 2

### 4. Initialize the Application

1. Activate virtual environment:
    ```bash
    venv\Scripts\activate # or "source venv\bin\activate" in Linux
    ```

2. Apply database migrations:
    ```bash
    python manage.py migrate
    ```

3. Collect static files:
    ```bash
    python manage.py collectstatic
    ```

4. Load initial data (optional):
    ```bash
    python manage.py loaddata workflow/fixtures/initial_data.json
    ```

### 5. Start the Development Server

```bash
python manage.py runserver
```

The application will be available at http://127.0.0.1:8000

### 6. Xero Integration (Optional)

If you need Xero integration for local development:

1. Run ngrok for OAuth callbacks:
    ```bash
    python manage.py launch_ngrok
    ```
    This makes your local server available at msm-workflow.ngrok-free.app

2. Update your `.env` file with the Xero OAuth settings

## Production-like Setup

For a production-like environment with Xero/Dropbox integration:

1. Set `DJANGO_ENV=production_like` in your environment
2. Ensure Redis is installed and running (required for caching)
3. Start Celery for background tasks
4. Run with Gunicorn instead of the development server:
    ```bash
    gunicorn --bind 0.0.0.0:8000 jobs_manager.wsgi
    ```

## Troubleshooting

If you encounter any issues:

1. Ensure all dependencies are installed (`poetry install` and `npm install`)
2. Verify database connection settings in `.env`
3. Check the Django debug page for detailed error messages when in development mode
4. Review logs in the `logs/` directory for SQL and Xero integration issues