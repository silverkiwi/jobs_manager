## 🐛 Bugs

- **Add client crashes during the sync to Xero**.
- **MaterialEntry creation**: Invalid field name(s) for model `MaterialEntry`: `'comments', 'item_code', 'markup', 'rate', 'total'`.
- **Kanban board bug**: Error fetching quoting jobs – `TypeError: Cannot read properties of undefined (reading 'name')`.
- **Markup not working**: Jobs currently don't have markup functioning properly.  This means the link doesn't come up, or the client name
- **JobPricing not expanding**: It used to, but now we have scrollbars again.
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

## 🚀 Future Enhancements (Nice-to-Have Ideas)

- **Jobs don't support attachments**: Suggested fix – integrate with Dropbox or Google Drive for attachment support.
- **Look up contacts on a client**: Not implemented. Do we care enough to prioritize this feature?

## ❓ Uncertainties/Decisions

- **Many-to-one reverse relationship between jobs and pricing**: This isn't exactly a bug, but I'm not convinced this relationship is optimal.
- **Look up contacts on a client**: Not implemented. Do we care enough?
- **Solve the problem of shop jobs.  How do we easily say what particular shop job someone was working on.
- **Markup is broken, especially for materials**: What's the difference between cost rate and 