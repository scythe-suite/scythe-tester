from logging import StreamHandler, Formatter, INFO

from flask import Flask
from flask_restful import Resource, Api

from st.store import Store

app = Flask(__name__)
api = Api(app)

sh = StreamHandler()
sh.setLevel(INFO)
sh.setFormatter(Formatter('%(asctime)s [%(process)s] [%(levelname)s] Flask: %(name)s [in %(pathname)s:%(lineno)d] %(message)s', '%Y-%m-%d %H:%M:%S'))
app.logger.addHandler(sh)
app.logger.setLevel(INFO)
app.logger.info('Started redis rest server...')

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET')
    return response

class Uids(Resource):
    def get(self, session_id):
        s = Store(session_id)
        return {'uids': s.uids_getall()}

class Summaries(Resource):
    def get(self, session_id):
        s = Store(session_id)
        return {'summaries': s.summaries_getall()}

class Texts(Resource):
    def get(self, session_id):
        s = Store(session_id)
        return {'texts': s.texts_getall()}

class Cases(Resource):
    def get(self, session_id):
        s = Store(session_id)
        return {'cases':
            dict(
                (name, cases.to_list_of_dicts(('diffs', 'errors', 'actual')))
                for name, cases in s.cases_getall().items()
            )}

class Solutions(Resource):
    def get(self, uid, timestamp, exercise):
        s = Store()
        s.set_harvest(uid, timestamp)
        return {'solutions': s.solutions_get(exercise)}

class Compilations(Resource):
    def get(self, uid, timestamp, exercise):
        s = Store()
        s.set_harvest(uid, timestamp)
        return {'solutions': s.solutions_get(exercise)}

class Results(Resource):
    def get(self, uid, timestamp, exercise):
        s = Store()
        s.set_harvest(uid, timestamp)
        return {'solutions': s.solutions_get(exercise)}

api.add_resource(Uids, '/uids/<string:session_id>')
api.add_resource(Summaries, '/summaries/<string:session_id>')
api.add_resource(Texts, '/texts/<string:session_id>')
api.add_resource(Cases, '/cases/<string:session_id>')
api.add_resource(Solutions, '/solutions/<string:uid>/<string:timestamp>/<string:exercise>')
api.add_resource(Compilations, '/compilations/<string:uid>/<string:timestamp>/<string:exercise>')
api.add_resource(Results, '/results/<string:uid>/<string:timestamp>/<string:exercise>')
