#!/bin/bash

# Hourly update script for Africa Monitoring
# This script runs on Railway and updates data every hour

echo "=========================================="
echo "Africa Monitoring - Hourly Update"
echo "Time: $(date)"
echo "=========================================="

# Generate new data
python3 africa_monitor.py

# Check if generation was successful
if [ $? -eq 0 ]; then
    echo "✓ Data generation successful"
    
    # Copy to public directory
    if [ -f "/tmp/africa_data/africa_monitoring.json" ]; then
        cp /tmp/africa_data/africa_monitoring.json ./africa_monitoring.json
        echo "✓ Data file updated"
    else
        echo "✗ Data file not found"
    fi
else
    echo "✗ Data generation failed"
fi

echo "=========================================="
echo "Update complete"
echo "=========================================="

