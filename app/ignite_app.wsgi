#! /var/www/ignite/venv/bin/python3
# venv
import site
site.addsitedir('/var/www/ignite/venv/lib/python3.7/site-packages')

# logs
import sys
import logging
logging.basicConfig(stream=sys.stderr)

# Run app
sys.path.insert(0, '/var/www/ignite/')
sys.path.insert(0, '/var/www/ignite/app/')
from ignite_app import app as application
application.secret_key = 'thisissecret!'
