## 🐛 Bugs

- **Ugliness on job entry**: The word 'Revenue' isn't printed

- **Markup not working**: Jobs currently don't have markup functioning properly.  This means the link doesn't come up, or the client name
- **JobPricing not fully justified**: You can see the trash cans are not vertically aligned.
- **Autosave successful on failure**: You should only say successful if it passes
- **Duplicate time entries**: Not quite sure what's happening but I've seen multiple identical rows.  Probably relates to timesheet entry
- **Mins/item broke.**:  Estimate no longer saving it
- **The P&L report is pretty broken.  It's not doing category/subcategory.  It's not getting column names right.  Formatting is awful.  Low priority
- 
## 🛤️ Roadmap (Must-Have Features)

- **Suggested fix for markup**: Create a new 'markup' section to handle job markup properly. Example, time is normally marked up 30% while materials are normally marked up 20%.  This markup is **I think** a special TimeEntry, MaterialEntry, AdjustmentEntry, and it should be SHOWN in the table but should not be editable.
- **Copy estimate to quote**: Not yet implemented.
- **Revise quote**: Not yet implemented.
- **Submit quote to client**: Not yet implemented.
- **Need to export timesheets for IMS**. Not yet implemented
- **Create invoices in Xero**. Not yet implemented.
- **Timesheet week overview**. Not yet implemented.
- **Adding drawings to jobs**. Not yet implemented.  Need to tie into files (Dropbox) and to images (Google Photos)

## 🚀 Future Enhancements (Nice-to-Have Ideas)

- **Look up contacts on a client**: Not implemented. Do we care enough to prioritize this feature?
- **Tie in Google Maps** Improve the client data.  Add place_id for dedupe, and look up industry 
- **Phone Calls** Tie into phone calls.  Could grab SMS too
- **Balance Sheet** Useful??
- **Email** If this becomes the place we do everything, then it's easier to get all emails  
- **Delete** Since jobs autosave, it's very easy to get accidental jobs.  

## ❓ Uncertainties/Decisions

## Ideas for things to work on 2024-12-20

Understand the project
Understand ways of working

Understanding the app
GM, office manager, account manager, quotes manager

SHOP Jobs:
    Currently poorly handled.
    Maybe better to not have a number, e.g. SICK
    Important to have an estimate for each job, including shop jobs
    Maybe autogenerate them monthly, e.g. SICK-2024-12

Tests
Especially regression tests.  How to make the tests not break all the time

Code Linting

Quotes
You can copy estimates to quotes
You can 'archive' a quote
You can 'accept' a quote
You can email a quote to a customer

Purchases

Xero Linkage
Edit CLient
Create Invoice

Attach images to jobs

Search for archived jobs

Extranet
Clients can log in
Clients can see past jobs
