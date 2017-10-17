from os import environ

from st.web import app

def main():
    app.run(host = '0.0.0.0', port = int(environ.get('PORT', 8000)))
