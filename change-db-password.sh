#!/usr/bin/env bash
# Helper script to change database credentials safely.
#
# Usage:
#   ./change-db-password.sh
#
# This script will:
#   1. Prompt for the new PostgreSQL user and password
#   2. Update the .env file with the new credentials
#   3. Rebuild and restart the database container
#   4. The custom entrypoint will sync the new password into the running database
#
# The database data is preserved — no data loss.
set -euo pipefail

cd "$(dirname "$0")"

# Check for .env file
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env first."
    exit 1
fi

echo "=== LC-MS Database Credential Change ==="
echo ""
echo "This will update the PostgreSQL credentials in .env and restart the database."
echo "Your data will be preserved."
echo ""

# Get current values
CURRENT_USER=$(grep '^POSTGRES_USER=' .env | cut -d= -f2)
CURRENT_DB=$(grep '^POSTGRES_DB=' .env | cut -d= -f2)
echo "Current user: ${CURRENT_USER}"
echo "Current database: ${CURRENT_DB}"
echo ""

read -rp "New PostgreSQL user [keep '${CURRENT_USER}']: " NEW_USER
NEW_USER=${NEW_USER:-$CURRENT_USER}

read -rsp "New PostgreSQL password: " NEW_PASSWORD
echo ""
if [ -z "$NEW_PASSWORD" ]; then
    echo "ERROR: Password cannot be empty."
    exit 1
fi
read -rsp "Confirm password: " CONFIRM_PASSWORD
echo ""
if [ "$NEW_PASSWORD" != "$CONFIRM_PASSWORD" ]; then
    echo "ERROR: Passwords do not match."
    exit 1
fi

echo ""
echo "Updating .env file..."

# Update .env file
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed
    sed -i '' "s/^POSTGRES_USER=.*/POSTGRES_USER=${NEW_USER}/" .env
    sed -i '' "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${NEW_PASSWORD}/" .env
    sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://${NEW_USER}:${NEW_PASSWORD}@db:5432/${CURRENT_DB}|" .env
else
    # GNU sed
    sed -i "s/^POSTGRES_USER=.*/POSTGRES_USER=${NEW_USER}/" .env
    sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${NEW_PASSWORD}/" .env
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://${NEW_USER}:${NEW_PASSWORD}@db:5432/${CURRENT_DB}|" .env
fi

echo ".env updated."
echo ""
echo "Rebuilding and restarting the database container..."
echo "The custom entrypoint will sync the new password automatically."
echo ""

docker compose up -d --build db
echo ""
echo "Waiting for database to be healthy..."
sleep 5

# Restart backend to pick up new DATABASE_URL
echo "Restarting backend..."
docker compose up -d --build backend

echo ""
echo "=== Done ==="
echo "Database credentials have been updated and the app restarted."
echo "Verify the app is working by visiting http://localhost:18780"
