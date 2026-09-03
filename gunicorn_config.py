import os
bind = os.environ.get('BIND', '0.0.0.0:' + os.environ.get('PORT', '5000'))
workers = 3
threads = 2
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
loglevel = "info"
preload_app = True
worker_class = "sync"
