#!/bin/bash
# Setup cron jobs for hierarchical summarization system
# Run this script once to set up automatic summarization

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRON_LOG="$PROJECT_DIR/logs/cron.log"

echo "Setting up cron jobs for hierarchical summarization..."
echo "Project directory: $PROJECT_DIR"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/logs"

# Get current crontab
crontab -l > /tmp/current_crontab 2>/dev/null || touch /tmp/current_crontab

# Check if cron jobs already exist
if grep -q "weekly_summary.py" /tmp/current_crontab; then
    echo "⚠️  Weekly summary cron job already exists"
else
    echo "Adding weekly summary cron job (every Sunday at midnight)..."
    echo "0 0 * * 0 cd $PROJECT_DIR && python3 scripts/weekly_summary.py >> $CRON_LOG 2>&1" >> /tmp/current_crontab
fi

if grep -q "monthly_summary.py" /tmp/current_crontab; then
    echo "⚠️  Monthly summary cron job already exists"
else
    echo "Adding monthly summary cron job (1st of month at 1 AM)..."
    echo "0 1 1 * * cd $PROJECT_DIR && python3 scripts/monthly_summary.py >> $CRON_LOG 2>&1" >> /tmp/current_crontab
fi

if grep -q "yearly_summary.py" /tmp/current_crontab; then
    echo "⚠️  Yearly summary cron job already exists"
else
    echo "Adding yearly summary cron job (Jan 1st at 2 AM)..."
    echo "0 2 1 1 * cd $PROJECT_DIR && python3 scripts/yearly_summary.py && python3 scripts/archive_old_data.py >> $CRON_LOG 2>&1" >> /tmp/current_crontab
fi

# Install the new crontab
crontab /tmp/current_crontab
rm /tmp/current_crontab

echo ""
echo "✅ Cron jobs installed successfully!"
echo ""
echo "Current cron jobs:"
crontab -l | grep -E "(weekly|monthly|yearly)_summary"
echo ""
echo "To view cron logs: tail -f $CRON_LOG"
echo "To edit cron jobs: crontab -e"
echo "To list all cron jobs: crontab -l"

