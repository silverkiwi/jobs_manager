#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from datetime import datetime, timedelta

# --- Config ---
LOCAL_BACKUP_ROOT = "/var/backups/jobs_manager"
RCLONE_REMOTE = "gdrive:msm_backups"
DRY_RUN = "--delete" not in sys.argv
# ---------------

now = datetime.now()
RECENT_LIMIT = now - timedelta(hours=24)
DAILY_LIMIT = now - timedelta(days=7)


def parse_timestamp(dir_name):
    """
    Parse directory name of form YYYYMMDD_HHMMSS to datetime, else None.
    """
    try:
        return datetime.strptime(dir_name, "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def rclone_delete_dir(timestamp_dir):
    """
    Delete (purge) a remote timestamped folder.
    """
    remote_path = f"{RCLONE_REMOTE}/{timestamp_dir}"
    cmd = ["rclone", "purge", remote_path]
    if DRY_RUN:
        print(f"[DRY RUN] Would delete remote: {remote_path}")
    else:
        print(f"Deleting remote: {remote_path}")
        subprocess.run(cmd, check=False)


def delete_local_dir(path):
    """
    Remove a local backup directory.
    """
    if DRY_RUN:
        print(f"[DRY RUN] Would delete local: {path}")
    else:
        print(f"Deleting local: {path}")
        shutil.rmtree(path)


def main():
    # Gather all timestamped subdirectories
    entries = [d for d in os.listdir(LOCAL_BACKUP_ROOT)
               if os.path.isdir(os.path.join(LOCAL_BACKUP_ROOT, d))]
    dirs = []
    for d in entries:
        ts = parse_timestamp(d)
        if ts:
            dirs.append((d, ts))

    if not dirs:
        print("No valid backup directories found.")
        return

    # Sort oldest → newest
    dirs.sort(key=lambda x: x[1])

    keep = set()
    # 1) Always keep the latest
    latest = max(dirs, key=lambda x: x[1])[0]
    keep.add(latest)

    # 2) Keep all from last 24h
    for name, ts in dirs:
        if ts > RECENT_LIMIT:
            keep.add(name)

    # 3) One per day for past week
    seen_days = set()
    for name, ts in reversed(dirs):
        if RECENT_LIMIT >= ts > DAILY_LIMIT:
            day_key = (ts.year, ts.month, ts.day)
            if day_key not in seen_days:
                keep.add(name)
                seen_days.add(day_key)

    # 4) One per month (oldest)
    month_groups = {}
    for name, ts in dirs:
        month_key = (ts.year, ts.month)
        if month_key not in month_groups or ts < month_groups[month_key][1]:
            month_groups[month_key] = (name, ts)
    for name, _ in month_groups.values():
        keep.add(name)

    # Report
    print("\n--- Kept backups ---")
    for name in sorted(keep):
        print(f"Keeping: {name}")
    print("--- End keep list ---\n")

    # Delete unneeded
    for name, _ in dirs:
        if name in keep:
            continue
        full_path = os.path.join(LOCAL_BACKUP_ROOT, name)
        delete_local_dir(full_path)
        rclone_delete_dir(name)


if __name__ == "__main__":
    main()