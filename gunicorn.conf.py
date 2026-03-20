"""
Gunicorn production configuration for JobFinder.
Run with: gunicorn -c gunicorn.conf.py "app:app"
"""
import os
import multiprocessing

# ── Server socket ──────────────────────────────────────────
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:5000')

# ── Workers ────────────────────────────────────────────────
# Rule of thumb: (2 × CPU cores) + 1
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'         # Use 'gevent' if you install gevent
threads = 2                   # Threads per worker (sync class)
worker_connections = 1000     # Max simultaneous clients (async workers)
max_requests = 1000           # Restart worker after N requests (memory leak prevention)
max_requests_jitter = 50      # Add randomness to prevent thundering herd

# ── Timeouts ───────────────────────────────────────────────
timeout = 30                  # Kill worker if not responding for 30s
keepalive = 5                 # Keep-alive connections for 5s
graceful_timeout = 30         # Wait 30s for workers to finish on shutdown

# ── Logging ────────────────────────────────────────────────
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')   # '-' = stdout
errorlog  = os.environ.get('GUNICORN_ERROR_LOG', '-')    # '-' = stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# ── Process naming ─────────────────────────────────────────
proc_name = 'jobfinder'

# ── Security ───────────────────────────────────────────────
limit_request_line = 4094       # Max HTTP request-line size
limit_request_fields = 100      # Max HTTP headers
limit_request_field_size = 8190 # Max header field size
