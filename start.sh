#!/bin/bash

# Start script for Africa Monitoring on Railway
# Runs web server immediately, updates data in background

echo "Starting Africa Monitoring..."

# Make update script executable
chmod +x update_hourly.sh

# Start web server immediately
echo "Starting web server on port ${PORT:-8080}..."
node africa-server.js &
SERVER_PID=$!

echo "Web server started (PID: $SERVER_PID)"

# Run first data generation after 60 seconds (so server can start quickly)
echo "Scheduling first data update in 60 seconds..."
(sleep 60 && ./update_hourly.sh) &

# Run hourly updates in loop
echo "Starting hourly update loop..."
while true; do
    sleep 3600  # Wait 1 hour
    echo ""
    echo "Running scheduled update..."
    ./update_hourly.sh
done &

# Wait for server process
wait $SERVER_PID

