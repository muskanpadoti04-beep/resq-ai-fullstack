"""
RESQ AI - runtime configuration (all values can be overridden with environment variables / .env)
"""
import os

# Sensor data older than this is shown as STALE instead of being trusted silently.
STALE_MINUTES = int(os.getenv("RESQ_STALE_MINUTES", "120"))

# Signing key for login tokens. CHANGE THIS for any real deployment.
SECRET_KEY = os.getenv("RESQ_SECRET_KEY", "resq-ai-dev-secret-change-me")
TOKEN_HOURS = int(os.getenv("RESQ_TOKEN_HOURS", "12"))

# Set RESQ_AUTH=off to run the API without login (e.g. quick local demos / tests).
AUTH_ENABLED = os.getenv("RESQ_AUTH", "on").strip().lower() not in ("off", "0", "false", "no")

# Login throttling: after this many failed logins a user is locked out briefly.
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 60

LIFECYCLE = ["Detected", "Acknowledged", "Assigned", "En Route", "On Scene", "Resolved"]

# Sensor gateways / devices send this in the X-Device-Key header instead of a user login.
# CHANGE for any real deployment (demo value only).
DEVICE_API_KEY = os.getenv("RESQ_DEVICE_KEY", "resq-device-demo-key")

# An active incident nobody acknowledged within this many minutes is escalated (repeats every period).
ESCALATE_MINUTES = float(os.getenv("RESQ_ESCALATE_MINUTES", "2"))
# Old incidents (e.g. historic demo data) are not escalated: only those detected within this many hours.
ESCALATE_MAX_AGE_HOURS = float(os.getenv("RESQ_ESCALATE_MAX_AGE_HOURS", "24"))
ESCALATION_CHECK_SECONDS = int(os.getenv("RESQ_ESCALATION_CHECK_SECONDS", "20"))

# A camera that has not reported within this many minutes is shown offline.
CAMERA_STALE_MINUTES = int(os.getenv("RESQ_CAMERA_STALE_MINUTES", "10"))
