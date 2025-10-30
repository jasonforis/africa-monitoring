#!/bin/bash

# Start script for Africa Monitoring on Railway
# Runs web server and hourly data updates

echo "Starting Africa Monitoring..."

# Make update script executable
chmod +x update_hourly.sh

# Run initial data generation
echo "Running initial data generation..."
./update_hourly.sh

# Start web server in background
echo "Starting web server on port ${PORT:-3001}..."
node africa-server.js &
SERVER_PID=$!

# Wait a bit for server to start
sleep 3

echo "Web server started (PID: $SERVER_PID)"

# Run hourly updates in loop
echo "Starting hourly update loop..."
while true; do
    sleep 3600  # Wait 1 hour
    echo ""
    echo "Running scheduled update..."
    ./update_hourly.sh
done

