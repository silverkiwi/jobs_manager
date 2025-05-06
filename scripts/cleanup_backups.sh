#!/bin/bash
source /home/django_user/jobs_manager/.venv/bin/activate
python /usr/local/bin/cleanup_backups.py "$@"