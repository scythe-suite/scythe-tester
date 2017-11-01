from os import environ

from st.rest import socketio, app, pubsub_forwarder

def main():
    socketio.start_background_task(target = pubsub_forwarder)
    socketio.run(app, debug = True, use_reloader = False, host = '0.0.0.0', port = int(environ.get('PORT', 8000)))
