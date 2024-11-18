## 🐛 Bugs

- **Add client crashes during the sync to Xero**.
- **Markup not working**: Jobs currently don't have markup functioning properly.  This means the link doesn't come up, or the client name
- **JobPricing not fully justified**: It looks a bit ugly.
- **Autosave successful on failure**: You should only say successful if it passes

## 🛤️ Roadmap (Must-Have Features)

- **Suggested fix for markup**: Create a new 'markup' section to handle job markup properly. Example, time is normally marked up 30% while materials are normally marked up 20%.  This markup is **I think** a special TimeEntry, MaterialEntry, AdjustmentEntry, and it should be SHOWN in the table but should not be editable.
- **Copy estimate to quote**: Not yet implemented.
- **Revise quote**: Not yet implemented.
- **Submit quote to client**: Not yet implemented.
- **Check job as 'all fields complete'**: Feature not yet implemented.
- **Need to handle timesheet entry**.
- **Reporting: start with P&L**.
- **Need to export timesheets for IMS**.
- **Kanban should say job x of y**.

## 🚀 Future Enhancements (Nice-to-Have Ideas)

- **Jobs don't support attachments**: Suggested fix – integrate with Dropbox AND Google PHOTOS for attachment support.
- **Look up contacts on a client**: Not implemented. Do we care enough to prioritize this feature?
- **Tie in Google Maps** Improve the client data.  Add place_id for dedupe, and look up industry 

## ❓ Uncertainties/Decisions

- **Solve the problem of shop jobs.  How do we easily say what particular shop job someone was working on.
- **Markup is broken, especially for materials**: What's the difference between cost rate and 