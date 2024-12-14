# jobs_manager
Jobs/quotes/work management

Similar idea to django-timepiece

But customised to Morris Sheetmetals requirements.

A simple CRM with projects and businesses
User dashboards with budgeted hours based on project contracts
Time sheets with daily, weekly, and monthly summaries
Verified, approved, and invoiced time sheet workflows
Monthly payroll reporting with overtime, paid leave, and vacation summaries
Project invoicing with hourly summaries

## Installation

You'll need Python - poetry takes care of the packages 
You'll need node.  It's barely used, just npm to manage JS, but you still need it installed

You'll need to write your .env file, 
DEBUG=true or false
SECRET_KEY=For Django
ALLOWED_HOSTS=your hostnames
XERO_CLIENT_ID=From the Xero developer portal
XERO_CLIENT_SECRET=From the Xero developer portal
XERO_REDIRECT_URI=URL to redirect to after Xero login
DB_PASSWORD=Your database password
DROPBOX_ACCESS_TOKEN=Your dropbox access token

You'll need to install the fixtures

You'll then want to click the Refresh Xero data button.
