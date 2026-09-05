#!/bin/sh
# Custom PostgreSQL entrypoint that syncs credentials on every start.
#
# Problem: The official postgres:16-alpine image only honors POSTGRES_USER /
# POSTGRES_PASSWORD when the data directory is empty (first init). If you change
# these env vars after the volume already has data, the old credentials persist
# and the backend can't connect.
#
# Solution: Run the official entrypoint in the background, wait for Postgres to
# be ready, then ALTER the user's password to match the current env var. This
# makes credential changes in .env take effect on the next `docker compose up`
# without wiping the database.
#
# If POSTGRES_USER is changed to a name that doesn't exist in the database,
# this script creates the new user and grants it access to the existing data.
#
# The script remembers the original POSTGRES_USER in a marker file inside the
# data directory, so it can always connect as the original superuser to perform
# credential sync — even after the env var is changed.
set -e

PG_USER="${POSTGRES_USER:-lcms}"
PG_PASSWORD="${POSTGRES_PASSWORD:-changeme}"
PG_DB="${POSTGRES_DB:-lcms}"
PGDATA="${PGDATA:-/var/lib/postgresql/data}"

MARKER_FILE="${PGDATA}/.lcms_original_user"

# Start the official postgres entrypoint in the background
/usr/local/bin/docker-entrypoint.sh "$@" &
PG_PID=$!

# Wait for PostgreSQL to accept connections
echo "[pg-sync] Waiting for PostgreSQL to start..."
i=0
while [ $i -lt 90 ]; do
    if su postgres -c "pg_isready -q" 2>/dev/null; then
        sleep 1
        echo "[pg-sync] PostgreSQL is ready."
        break
    fi
    i=$((i + 1))
    sleep 1
done

if ! su postgres -c "pg_isready -q" 2>/dev/null; then
    echo "[pg-sync] ERROR: PostgreSQL did not start within 90s."
    exit 1
fi

# --- Determine the original superuser role -----------------------------------
# The official entrypoint creates the superuser role named after POSTGRES_USER
# on first init. After that, the env var can be changed but the role persists.
# We store the original user in a marker file so we can always connect.

ADMIN_ROLE=""

# Try the marker file first (records the original user from first init)
if [ -f "${MARKER_FILE}" ]; then
    MARKER_USER=$(cat "${MARKER_FILE}")
    echo "[pg-sync] Found original user from marker: '${MARKER_USER}'"
    # Verify this role still exists and is a superuser
    EXISTS=$(su postgres -c "psql -U '${MARKER_USER}' -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${MARKER_USER}' AND rolsuper=true\"" 2>/dev/null || echo "")
    if [ "${EXISTS}" = "1" ]; then
        ADMIN_ROLE="${MARKER_USER}"
    fi
fi

# If no marker or marker user doesn't exist, try the current POSTGRES_USER
if [ -z "${ADMIN_ROLE}" ]; then
    EXISTS=$(su postgres -c "psql -U '${PG_USER}' -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}' AND rolsuper=true\"" 2>/dev/null || echo "")
    if [ "${EXISTS}" = "1" ]; then
        ADMIN_ROLE="${PG_USER}"
    fi
fi

# If still no admin role, try "postgres" (default for some installations)
if [ -z "${ADMIN_ROLE}" ]; then
    EXISTS=$(su postgres -c "psql -U postgres -tAc \"SELECT 1 FROM pg_roles WHERE rolname='postgres' AND rolsuper=true\"" 2>/dev/null || echo "")
    if [ "${EXISTS}" = "1" ]; then
        ADMIN_ROLE="postgres"
    fi
fi

# Last resort: scan for any superuser role by trying common names
if [ -z "${ADMIN_ROLE}" ]; then
    echo "[pg-sync] Could not find admin role via env vars. Scanning..."
    # Try connecting as each role that might exist
    for candidate in lcms postgres admin root db; do
        EXISTS=$(su postgres -c "psql -U '${candidate}' -tAc \"SELECT rolname FROM pg_roles WHERE rolsuper=true LIMIT 1\"" 2>/dev/null || echo "")
        if [ -n "${EXISTS}" ]; then
            ADMIN_ROLE="${EXISTS}"
            echo "[pg-sync] Found superuser: '${ADMIN_ROLE}'"
            break
        fi
    done
fi

if [ -z "${ADMIN_ROLE}" ]; then
    echo "[pg-sync] ERROR: Could not find a superuser role to connect with."
    echo "[pg-sync] The database may need to be reinitialized (remove the db_data volume)."
    wait $PG_PID
    exit 0
fi

echo "[pg-sync] Using admin role '${ADMIN_ROLE}' to sync credentials."

# --- Write marker file for future starts -------------------------------------
# Record the original user so future restarts can find it even if POSTGRES_USER
# is changed again
if [ ! -f "${MARKER_FILE}" ]; then
    echo "${ADMIN_ROLE}" > "${MARKER_FILE}"
    echo "[pg-sync] Recorded original user '${ADMIN_ROLE}' in marker file."
fi

# --- Sync credentials --------------------------------------------------------
echo "[pg-sync] Syncing credentials for user '${PG_USER}'..."

USER_EXISTS=$(su postgres -c "psql -U '${ADMIN_ROLE}' -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'\"" 2>/dev/null || echo "")

if [ "${USER_EXISTS}" = "1" ]; then
    # User exists — update password to match env var
    su postgres -c "psql -U '${ADMIN_ROLE}' -c \"ALTER USER \\\"${PG_USER}\\\" WITH PASSWORD '${PG_PASSWORD}' SUPERUSER;\"" >/dev/null 2>&1
    echo "[pg-sync] Password updated for existing user '${PG_USER}'."
else
    # User doesn't exist — create with superuser privileges
    echo "[pg-sync] User '${PG_USER}' not found. Creating..."
    su postgres -c "psql -U '${ADMIN_ROLE}' -c \"CREATE USER \\\"${PG_USER}\\\" WITH SUPERUSER PASSWORD '${PG_PASSWORD}';\"" >/dev/null 2>&1

    DB_EXISTS=$(su postgres -c "psql -U '${ADMIN_ROLE}' -tAc \"SELECT 1 FROM pg_database WHERE datname='${PG_DB}'\"" 2>/dev/null || echo "")
    if [ "${DB_EXISTS}" = "1" ]; then
        su postgres -c "psql -U '${ADMIN_ROLE}' -c \"GRANT ALL PRIVILEGES ON DATABASE \\\"${PG_DB}\\\" TO \\\"${PG_USER}\\\";\"" >/dev/null 2>&1
        su postgres -c "psql -U '${ADMIN_ROLE}' -d \"${PG_DB}\" -c \"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \\\"${PG_USER}\\\";\"" >/dev/null 2>&1
        su postgres -c "psql -U '${ADMIN_ROLE}' -d \"${PG_DB}\" -c \"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \\\"${PG_USER}\\\";\"" >/dev/null 2>&1
        su postgres -c "psql -U '${ADMIN_ROLE}' -d \"${PG_DB}\" -c \"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \\\"${PG_USER}\\\";\"" >/dev/null 2>&1
        su postgres -c "psql -U '${ADMIN_ROLE}' -d \"${PG_DB}\" -c \"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO \\\"${PG_USER}\\\";\"" >/dev/null 2>&1
        echo "[pg-sync] Granted access to existing database '${PG_DB}'."
    else
        su postgres -c "psql -U '${ADMIN_ROLE}' -c \"CREATE DATABASE \\\"${PG_DB}\\\" OWNER \\\"${PG_USER}\\\";\"" >/dev/null 2>&1
        echo "[pg-sync] Created database '${PG_DB}'."
    fi
fi

echo "[pg-sync] Credential sync complete."

# Bring the official entrypoint to the foreground
wait $PG_PID
