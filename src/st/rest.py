from json import loads
from logging import StreamHandler, Formatter, INFO
from os import environ

from flask import Flask, request
from flask_restful import Resource, Api, abort
from flask_socketio import SocketIO, emit

from st.store import Store

PUBSUB_SLEEP_SECONDS = 5

app = Flask(__name__)
api = Api(app)
socketio = SocketIO(app, async_mode = 'eventlet')

sh = StreamHandler()
sh.setLevel(INFO)
sh.setFormatter(Formatter('%(asctime)s [%(process)s] [%(levelname)s] Flask: %(name)s [in %(pathname)s:%(lineno)d] %(message)s', '%Y-%m-%d %H:%M:%S'))
app.logger.addHandler(sh)
app.logger.setLevel(INFO)
app.logger.info('Started redis rest server...')

# @app.after_request
# def after_request(response):
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
#     response.headers.add('Access-Control-Allow-Methods', 'GET')
#     return response

def check_auth(store, realm):
    try:
        auth = request.args['auth']
    except KeyError:
        auth = None
    realms = store.sessions_loads(auth)
    print realms
    if (realm == 'summaries' and 'private' not in realms): return
    if ('all' in realms) or (realm in realms): return
    abort(401)

def pubsub_forwarder():
    import redis
    app.logger.info('Started pub/sub forwarder')
    r = redis.StrictRedis.from_url('redis://{}'.format(environ.get('SCYTHE_REDIS_HOST', 'localhost')))
    p = r.pubsub()
    p.subscribe('summaries_channel')
    while True:
        socketio.emit('load_message', {'load': Store.jobs_num()})
        message = p.get_message()
        if message and message['type'] == 'message' and message['channel'] == 'summaries_channel':
            socketio.emit('summary_message', {'summary': loads(message['data'])})
            app.logger.info('Forwarded a new result to websocket')
            continue
        socketio.sleep(PUBSUB_SLEEP_SECONDS)

class Sessions(Resource):
    def get(self):
        return {'sessions': Store.get_sessions()}

class Uids(Resource):
    def get(self, session_id):
        s = Store(session_id)
        return {'uids': s.uids_getall()}

class Exercises(Resource):
    def get(self, session_id):
        s = Store(session_id)
        return {'exercises': s.texts_exercises()}

class Summaries(Resource):
    def get(self, session_id):
        s = Store(session_id)
        check_auth(s, 'summaries')
        return {'summaries': s.summaries_getall()}

class Texts(Resource):
    def get(self, session_id):
        s = Store(session_id)
        check_auth(s, 'texts')
        return {'texts': s.texts_getall()}

class Cases(Resource):
    def get(self, session_id):
        s = Store(session_id)
        check_auth(s, 'cases')
        return {'cases':
            dict(
                (name, cases.to_list_of_dicts(('diffs', 'errors', 'actual')))
                for name, cases in s.cases_getall().items()
            )}

class Solutions(Resource):
    def get(self, session_id, uid, timestamp, exercise):
        s = Store(session_id)
        check_auth(s, 'solutions')
        s.set_harvest(uid, timestamp)
        return {'solutions': s.solutions_get(exercise)}

class Compilations(Resource):
    def get(self, session_id, uid, timestamp, exercise):
        s = Store(session_id)
        check_auth(s, 'compilations')
        s.set_harvest(uid, timestamp)
        return {'compilations': s.compilations_get(exercise)}

class Results(Resource):
    def get(self, session_id, uid, timestamp, exercise):
        s = Store(session_id)
        check_auth(s, 'results')
        s.set_harvest(uid, timestamp)
        return {'results': s.results_get(exercise)}

api.add_resource(Sessions, '/sessions')
api.add_resource(Uids, '/uids/<string:session_id>')
api.add_resource(Exercises, '/exercises/<string:session_id>')
api.add_resource(Summaries, '/summaries/<string:session_id>')
api.add_resource(Texts, '/texts/<string:session_id>')
api.add_resource(Cases, '/cases/<string:session_id>')
api.add_resource(Solutions, '/solutions/<string:session_id>/<string:uid>/<string:timestamp>/<string:exercise>')
api.add_resource(Compilations, '/compilations/<string:session_id>/<string:uid>/<string:timestamp>/<string:exercise>')
api.add_resource(Results, '/results/<string:session_id>/<string:uid>/<string:timestamp>/<string:exercise>')

@socketio.on('connect')
def client_connect():
    app.logger.info('Client connected')

@socketio.on('disconnect')
def client_disconnect():
    app.logger.info('Client disconnected')
