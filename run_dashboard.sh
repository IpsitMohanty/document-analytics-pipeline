#!/bin/bash
# Usage: bash run_dashboard.sh "postgresql://..." "yourpassword"
export DATABASE_URL="$1"
export DASHBOARD_PASSWORD="$2"
streamlit run dashboard/app.py
