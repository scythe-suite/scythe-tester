from base64 import decodestring, encodestring
from json import loads, dumps
from logging import Handler, Formatter, getLogger, INFO, WARN
from os import environ
from time import time, sleep

from itsdangerous import URLSafeSerializer, BadSignature

from redis import StrictRedis, BusyLoadingError

from sf.testcases import TestCases

from st import TEST_UID


class RedisHandler(Handler):
    MAX_MESSAGES = 1000
    KEY = 'log'
    FORMATTER = Formatter('%(process)d|%(asctime)s|%(levelname)s|%(message)s', '%Y-%m-%d %H:%M:%S')
    def __init__(self, redis):
        super(RedisHandler, self).__init__(WARN)
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


def _connect():
    client = StrictRedis.from_url('redis://{}'.format(environ.get('SCYTHE_REDIS_HOST', 'localhost')))
    start_time = time()
    while time() - start_time < 10: # wait at most 10s
        try:
            client.get(None)
        except BusyLoadingError:
            sleep(0.1)
        else:
            break
    return client


class Store(object):

    REDIS = _connect()
    JOBS_KEY = 'jobs'
    SESSIONS_KEY = 'sessions'
    LOGGER = getLogger('STORE_LOGGER')
    LOGGER.setLevel(INFO)
    LOGGER.addHandler(RedisHandler(REDIS))

    def __init__(self, session_id = ''):
        self.session_id = session_id
        self.uids_key = 'uids:{}'.format(session_id)
        self.cases_key = 'cases:{}'.format(session_id)
        self.texts_key = 'texts:{}'.format(session_id)
        self.summaries_key = 'summaries:{}'.format(session_id)

    @staticmethod
    def get_logentry(follow):
        if follow:
            return Store.REDIS.blpop('log', 0)[1]
        else:
            return Store.REDIS.lpop('log')

    @staticmethod
    def get_sessions():
        return Store.REDIS.hkeys(Store.SESSIONS_KEY)

    @staticmethod
    def jobs_clean():
        Store.REDIS.delete(Store.JOBS_KEY)

    @staticmethod
    def jobs_enqueue(session_id, uid, timestamp, tar_data, clean = False):
        job = {'tar_data': encodestring(tar_data), 'session_id': session_id, 'uid': uid, 'timestamp': timestamp, 'clean': clean}
        Store.REDIS.rpush(Store.JOBS_KEY, dumps(job))

    @staticmethod
    def jobs_dequeue():
        try:
            job = Store.REDIS.blpop(Store.JOBS_KEY, 0)
        except KeyboardInterrupt:
            Store.LOGGER.info('Job dequeueing interrupted')
            return None
        job = loads(job[1])
        job['tar_data'] = decodestring(job['tar_data'])
        return job

    @staticmethod
    def jobs_num():
        return Store.REDIS.llen(Store.JOBS_KEY)

    def set_harvest(self, uid, timestamp = None):
        self.uid = uid
        self.timestamps_key = 'timestamps:{}:{}'.format(self.session_id, uid)
        if timestamp is None:
            last = Store.REDIS.zrange(self.timestamps_key, -1, -1)
            if not last: return None
            timestamp = last[0]
        self.timestamp = timestamp
        self.solutions_key = 'solutions:{}:{}'.format(uid, timestamp)
        self.compilations_key = 'compilations:{}:{}'.format(uid, timestamp)
        self.results_key = 'results:{}:{}'.format(uid, timestamp)
        return timestamp

    def uids_clean(self):
        Store.REDIS.delete(self.uids_key)

    def uids_addall(self, uids_infos, status = 'registered'):
        n = 0
        for uid, info in uids_infos:
            if uid == TEST_UID: continue
            n += Store.REDIS.sadd(self.uids_key, dumps({'uid': uid, 'info': info, 'status': status}))
        return n

    def uids_getall(self):
        juids = Store.REDIS.smembers(self.uids_key)
        if juids:
            return list(map(loads, juids))
        else:
            return []

    def cases_clean(self):
        Store.REDIS.delete(self.cases_key)

    def cases_add(self, exercise_name, cases):
        list_of_cases = cases.to_list_of_dicts(('diffs', 'errors', 'actual'))
        Store.REDIS.hset(self.cases_key, exercise_name, dumps(list_of_cases))
        return len(list_of_cases)

    def cases_get(self, exercise_name):
        cases = Store.REDIS.hget(self.cases_key, exercise_name)
        if cases:
            return TestCases.from_list_of_dicts(loads(cases))
        else:
            return TestCases()

    def cases_getall(self):
        cases = Store.REDIS.hgetall(self.cases_key)
        return dict((name, TestCases.from_list_of_dicts(loads(cases_list))) for name, cases_list in cases.items())

    def texts_clean(self):
        Store.REDIS.delete(self.texts_key)

    def texts_add(self, exercise_name, list_of_texts):
        Store.REDIS.hset(self.texts_key, exercise_name, dumps(list_of_texts))
        return len(list_of_texts)

    def texts_getall(self):
        texts = Store.REDIS.hgetall(self.texts_key)
        return dict((name, loads(texts_list)) for name, texts_list in texts.items())

    def texts_exercises(self):
        res = {}
        cases = Store.REDIS.hgetall(self.cases_key)
        for name in Store.REDIS.hkeys(self.texts_key):
            res[name] = len(loads(cases[name])) if name in cases else 0
        return res

    def timestamps_clean(self):
        Store.REDIS.zrem(self.timestamps_key, self.timestamp)

    def timestamps_contained(self):
        return Store.REDIS.zscore(self.timestamps_key, self.timestamp) is not None

    def timestamps_add(self):
        return Store.REDIS.zadd(self.timestamps_key, float(self.timestamp), self.timestamp)

    def solutions_clean(self):
        Store.REDIS.delete(self.solutions_key)

    def solutions_add(self, exercise_name, list_of_solutions):
        Store.REDIS.hset(self.solutions_key, exercise_name, dumps(list_of_solutions))
        return len(list_of_solutions)

    def solutions_get(self, exercise_name):
        solutions = Store.REDIS.hget(self.solutions_key, exercise_name)
        if solutions:
            return loads(solutions)
        else:
            return []

    def solutions_getall(self):
        solutions = Store.REDIS.hgetall(self.solutions_key)
        return dict((name, loads(solutions_list)) for name, solutions_list in solutions.items())

    def compilations_clean(self):
        Store.REDIS.delete(self.compilations_key)

    def compilations_add(self, exercise_name, compiler_message):
        return Store.REDIS.hset(self.compilations_key, exercise_name, compiler_message)

    def compilations_get(self, exercise_name):
        return Store.REDIS.hget(self.compilations_key, exercise_name)

    def compilations_getall(self):
        return Store.REDIS.hgetall(self.compilations_key)

    def results_clean(self):
        Store.REDIS.delete(self.results_key)

    def results_add(self, exercise_name, results):
        list_of_results = results.to_list_of_dicts(('input', 'args', 'expected'))
        Store.REDIS.hset(self.results_key, exercise_name, dumps(list_of_results))
        return len(list_of_results)

    def results_get(self, exercise_name):
        results = Store.REDIS.hget(self.results_key, exercise_name)
        if results:
            return loads(results)
        else:
            return []

    def results_getall(self):
        results = Store.REDIS.hgetall(self.results_key)
        return dict((name, TestCases.from_list_of_dicts(loads(results_list))) for name, results_list in results.items())

    def cases_clean(self):
        Store.REDIS.delete(self.cases_key)

    def summaries_clean(self):
        Store.REDIS.hdel(self.summaries_key, self.uid)

    def summaries_add(self, summary):
        Store.REDIS.hset(self.summaries_key, self.uid, dumps({
            'timestamp': self.timestamp,
            'summary': summary
        }))
        Store.REDIS.publish('summaries_channel',
        dumps({
            'session_id': self.session_id,
            'uid': self.uid,
            'timestamp': self.timestamp,
            'summary': summary
        }))

    def summaries_getall(self):
        summaries = Store.REDIS.hgetall(self.summaries_key)
        return dict((uid, loads(summary_list)) for uid, summary_list in summaries.items())

    def sessions_clean(self):
        Store.REDIS.hdel(self.SESSIONS_KEY, self.session_id)

    def sessions_add(self, secret):
        Store.REDIS.hset(self.SESSIONS_KEY, self.session_id, secret)

    def sessions_dumps(self, dct):
        return URLSafeSerializer(Store.REDIS.hget(self.SESSIONS_KEY, self.session_id)).dumps(dct)

    def sessions_loads(self, str):
        try:
            return URLSafeSerializer(Store.REDIS.hget(self.SESSIONS_KEY, self.session_id)).loads(str)
        except BadSignature:
            return {}
