## 🐛 First release milestone requirements

My plan is to go live with the app.  Ideally on the 13th of January.  That means

The app will be used for ALL data entry: estimates, quotes, timesheets, purchases, invoice generation, payroll export
The app will be the permanent archive of jobs from this release.  We will no longer store paper jobs

### Regressions

Functionality that used to work doesn't any more.  E.g. selecting the client for a job


### Estimate Entry

Probably sorted from a MVP perspective
The totals not calculating needs fixing

### Quotes Entry

Needs 'copy estimate to quote'
Needs 'approve quote'
Needs the MSM logo - quotes need to look official

### Timesheets

Requires weekly and daily view
Requires the ability to move time from one job to another
Requires resolving the data entry for internal jobs that roll month to month

### Purchases

Requires a page similar to timesheets for entering a purchase.
Much like a timesheet, it will create entries in the job(s) associated
Can link to a bill in Xero (must link to a bill eventually)
Can link to a Purchase Order in Xero (must link to a PO eventually)

### Jobs timeline

 A log of events related to a job (created, status changes, etc).  
    Some automated (e.g. stauts changes, some entered manually e.g. job picked up)

Essential governance feature.  
Xero calls this 'history and notes'.  They do NOT support editing of history or notes.
THey have a manual add notes 
Changes, Date, User, Details

### PDF Generation

Needs to look like our current printed jobs
E.g. logo, date ordered, delivery date, etc.

### Invoice Generation

The button 'generate invoice' creates the invoice in Xero 

### Payroll Export

Just seeing the data on screen for manually copy/pasting
Note the weekly view may be perfect for this

# Stuff that didn't make the first release

## Email quotes: (generates PDF, creates draft email containing PDF, launches Chrome)
## Testing

I'm not happy with the number of regressions.  Ideally I'd have some sort of test that ensured the app continues to work.  
My experience with automated testing is you end up spending longer maintaining the tests than you do writing software


## Budgeting

* Revenue targets/forecasts
* Time sick / away /shop targets/forecasts
* Integration with budgeting

## Basic business rules
You shoudln't invoice a job that isn't done
You shoudln't put time on a job that isn't approved (except time quoting)
You shoudln't change an invoice after it has been approved
You shoudln't change anything in reality pricing after a job is invoiced.

## Payroll export


----
Following is the old TODO

It's still mostly correct but... what I've done above is prioritise  
----


## 🐛 Bugs

- **Markup not working**: Jobs currently don't have markup functioning properly.  This means the link doesn't come up, or the client name
- **Autosave successful on failure**: You should only say successful if it passes
- **Duplicate time entries**: Not quite sure what's happening but I've seen multiple identical rows.  I think the reverse link should highlight the problem
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

Search for archived jobs

Extranet
Clients can log in
Clients can see past jobs
