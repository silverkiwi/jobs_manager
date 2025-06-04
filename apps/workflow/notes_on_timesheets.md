# Staff Time Entry System Design

## Overview
System to efficiently enter daily time cards while preventing common errors and providing immediate feedback. Focused on GM's workflow of processing ~10 physical time cards each morning.

## Job Structure

### Job Types
```
CLIENT    - Billable client work
OVERHEAD  - Necessary business activities
IDLE      - Underutilization
LEAVE     - Various types of leave
```

### Standard Non-Client Jobs
```
OVERHEAD:
- SHOP-MAINT  # Required shop maintenance
- ADMIN       # Meetings, quoting, client discussions

IDLE:
- SHOP-IDLE   # Underutilization/"busy work"

LEAVE:
- LEAVE-SICK
- LEAVE-ANNUAL
- LEAVE-SPECIAL
```

## User Interface Flow

### 1. Week Overview
```
[Week: 11-17 Nov 2024] [Change Week ▼]

Staff     | Mon | Tue | Wed | Thu | Fri | Total | Billable%
----------|-----|-----|-----|-----|-----|--------|----------
John      | 8.0 | 8.0 | 8.0 | 8.0 | --- |  32.0  |  85%
 └ Status | ✓   | ✓   | ✓   | ✓   | Off |        |
Paul      | 8.0 | 8.0 | --- | 8.0 | 8.0 |  32.0  |  75%
 └ Status | ✓   | ✓   |Leave| ✓   | ⚠   |        |

Weekly Totals: 64.0 hrs | Billable: 80% | Shop: 15% | Leave: 5%
```

### 2. Daily View
```
[Thursday, 14 Nov 2024] [Change Date ▼]

Staff Member  | Expected | Entered | Status    | Alerts
-------------|----------|----------|-----------|--------
John Smith   |   8.0    |   8.0    | Complete  | -
Paul Jones   |   8.0    |   6.5    | ⚠ Missing | 1.5hrs needed
Sarah Wilson |   8.0    |   8.5    | Complete  | ⚠ Overtime
Mike Brown   |   0.0    | -        | Off Today | -

Daily Totals: 23.0/24.0 hrs | Billable: 75% | Shop: 20% | Leave: 5%
```

### 3. Individual Time Entry
```
[Paul Jones - Thursday, 14 Nov 2024]
+------------------------+--------------------------------+
| Time Entry            | Job Details                    |
|------------------------|--------------------------------|
| Job#    Hours  Bill OT| Current Jobs:                  |
| [ABC123] [2.5] [✓] [ ]| ABC123 - Widget Repair        |
| [SH-MNT] [2.0] [ ] [ ]|  - Today: 2.5hrs              |
| [XYZ789] [2.0] [✓] [ ]|  - Total: 12/20 hrs (60%)     |
| [     ] [   ] [ ] [ ]|                                |
|                      | Recent Jobs:                    |
|                      | XYZ789 - Machine Install       |
|                      |  - Today: 2.0hrs               |
|                      |  - Total: 8/15 hrs (53%)       |
+----------------------+--------------------------------+
| Daily Summary: 6.5/8.0 hrs entered                    |
| Billable: 4.5hrs (69%) | Shop: 2.0hrs (31%)          |
| ⚠ Incomplete: 1.5 more hours needed                   |
+--------------------------------------------------------+
```

## Validation Rules

### Job Selection
1. First-time job warning:
```
⚠ First time Paul has worked on ABC123
   Job: Widget Repair for Acme Corp
   [Continue] [Cancel]
```

2. High shop time warning:
```
⚠ High shop time detected
   Paul has 4hrs (50%) on shop jobs today
   [Continue] [Cancel]
```

3. Job near/over estimate:
```
⚠ Job ABC123 approaching estimate
   Current: 18/20 hrs (90%)
   [Continue] [Cancel]
```

### Hours Validation
- Must sum to daily expected hours (usually 8)
- Overtime needs explicit flag
- Leave jobs must match approved leave records
- Shop-idle time triggers review at certain threshold

## Reporting Focus
1. Utilization:
   - Billable vs non-billable time
   - Shop time analysis
   - Leave patterns
2. Job Progress:
   - Hours vs estimates
   - Staff allocation
3. Business Health:
   - Idle time tracking
   - Overhead analysis

## Technical Notes
1. All times stored in minutes internally
2. Job type integrated into existing Job model
3. Validation happens real-time during entry
4. Export format needed for HR system

Would you like me to elaborate on any of these sections?