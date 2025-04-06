#!/bin/bash

# Start the application with the correct WSGI entry point
exec gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 wsgi:app
