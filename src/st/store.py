"""
 SET	uids:<SESSION_ID> -> JSON({uid : <UID>, info : <INFO>, status: <STATUS>})
HASH	texts:<SESSION_ID> -> <EXERCISE_NAME>: JSON({name: <TEXT_NAME>, content: <MARKDOWN_TEXT>})
HASH	cases:<SESSION_ID> -> <EXERCISE_NAME>: JSON([{name: <CASE_NAME>, args: <ARGS>, input: <INPUT>, expected: <EXPECTED>}+])

ZSET	timestamps:<SESSION_ID>:<UID> -> TIMESTAMP

HASH	solutions:<UID>:<TIMESTAMP> -> <EXERCISE_NAME>: JSON([{content: <SOURCE_CODE>, name: <FILE_NAME>}+])
HASH	results:<UID>:<TIMESTAMP> -> <EXERCISE_NAME>: JSON([{name: <CASE_NAME>, diffs: <ARGS>, errors: <INPUT>}+])
HASH	compilations:<UID>:<TIMESTAMP> -> <EXERCISE_NAME>: <COMPILER_OUTPUT>

HASH	summary:<SESSION_ID> -> <UID>: JSON([{name: <EXERCISE_NAME>, compile: <BOOLEAN>: diffs: <NUM_DIFFS>, errors: <NUM_ERRORS>, …}+])
"""

from base64 import decodestring, encodestring
from json import loads, dumps
from logging import Handler, Formatter, getLogger, INFO
from os import environ

from redis import StrictRedis

from sf.testcases import TestCases

from st import TEST_UID

POISON = '<POISON>'

class Store(object):

    REDIS = StrictRedis.from_url(environ.get('SCYTHE_REDIS_URL', 'redis://localhost'))

    def __init__(self, session_id):
        self.session_id = session_id
        self.jobs_key = 'jobs:{}'.format(session_id)
        self.uids_key = 'uids:{}'.format(session_id)
        self.cases_key = 'cases:{}'.format(session_id)
        self.texts_key = 'texts:{}'.format(session_id)
        self.logger = getLogger('PROCESS_LOG')
        self.logger.setLevel(INFO)
        self.logger.addHandler(RedisHandler(self.REDIS))

    @classmethod
    def getlogentry(cls, follow):
        if follow:
            return cls.REDIS.blpop('log', 0)[1]
        else:
            return cls.REDIS.lpop('log')

    def set_harvest(self, uid, timestamp):
        self.uid = uid
        self.timestamp = timestamp
        self.timestamps_key = 'timestamps:{}:{}'.format(self.session_id, uid)
        self.solutions_key = 'solutions:{}:{}'.format(uid, timestamp)
        self.compilations_key = 'compilations:{}:{}'.format(uid, timestamp)
        self.results_key = 'results:{}:{}'.format(uid, timestamp)

    def jobs_clean(self):
        Store.REDIS.delete(self.jobs_key)

    def jobs_enqueue(self, uid, timestamp, tar_data, clean = False):
        job = {'tar_data': encodestring(tar_data), 'uid': uid, 'timestamp': timestamp, 'clean': clean}
        Store.REDIS.rpush(self.jobs_key, dumps(job))

    def jobs_poison(self):
        Store.REDIS.rpush(self.jobs_key, POISON)

    def jobs_dequeue(self):
        try:
            job = Store.REDIS.blpop(self.jobs_key, 0)
        except KeyboardInterrupt:
            self.logger.info('Job dequeueing interrupted')
            job = None
        if job == POISON or job is None: return None
        job = loads(job[1])
        job['tar_data'] = decodestring(job['tar_data'])
        return job

    def uids_clean(self):
        Store.REDIS.delete(self.uids_key)

    def uids_add(self, uids_infos, status = 'registered'):
        n = 0
        for uid, info in uids_infos:
            if uid == TEST_UID: continue
            n += Store.REDIS.sadd(self.uids_key, dumps({'uid': uid, 'info': info, 'status': status}))
        return n

    def cases_clean(self):
        Store.REDIS.delete(self.cases_key)

    def cases_add(self, exercise_name, cases, kinds_to_skip = ()):
        list_of_cases = cases.to_list_of_dicts(kinds_to_skip)
        Store.REDIS.hset(self.cases_key, exercise_name, dumps(list_of_cases))
        return len(list_of_cases)

    def cases_get(self, exercise_name):
        cases = Store.REDIS.hget(self.cases_key, exercise_name)
        return TestCases.from_list_of_dicts(loads(cases))

    def texts_clean(self):
        Store.REDIS.delete(self.texts_key)

    def texts_add(self, exercise_name, list_of_texts):
        Store.REDIS.hset(self.texts_key, exercise_name, dumps(list_of_texts))
        return len(list_of_texts)

    def timestamps_clean(self):
        Store.REDIS.zrem(self.timestamps_key, self.timestamp)

    def timestamps_contains(self):
        return Store.REDIS.zscore(self.timestamps_key, timestamp) != 0

    def timestamps_add(self):
        return Store.REDIS.zadd(self.timestamps_key, self.timestamp, float(self.timestamp))

    def solutions_clean(self):
        Store.REDIS.delete(self.solutions_key)

    def solutions_add(self, exercise_name, list_of_solutions):
        Store.REDIS.hset(self.solutions_key, exercise_name, dumps(list_of_solutions))
        return len(list_of_solutions)

    def compilations_clean(self):
        Store.REDIS.delete(self.compilations_key)

    def compilations_add(self, exercise_name, compiler_message):
        return Store.REDIS.hset(self.compilations_key, exercise_name, compiler_message)

    def results_clean(self):
        Store.REDIS.delete(self.results_key)

    def results_add(self, exercise_name, cases):
        Store.REDIS.hset(self.results_key, exercise_name, dumps(cases.to_list_of_dicts(('input', 'args', 'expected'))))
        return len(cases)

class RedisHandler(Handler):
    MAX_MESSAGES = 1000
    KEY = 'log'
    FORMATTER = Formatter('%(process)d|%(asctime)s|%(levelname)s|%(message)s', '%Y-%m-%d %H:%M:%S')
    def __init__(self, redis):
        super(RedisHandler, self).__init__(INFO)
        self.redis = redis
    def emit(self, record):
        try:
            if self.MAX_MESSAGES:
                p = self.redis.pipeline()
                p.rpush(self.KEY, self.FORMATTER.format(record))
                p.ltrim(self.KEY, -self.MAX_MESSAGES, -1)
                p.execute()
            else:
                self.redis_client.rpush(self.KEY, self.FORMATTER.format(record))
        except:
            pass
