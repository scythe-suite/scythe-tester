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
from logging import Handler, Formatter, getLogger, INFO, WARN
from os import environ

from redis import StrictRedis

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


class Store(object):

    REDIS = StrictRedis.from_url(environ.get('SCYTHE_REDIS_URL', 'redis://localhost'))
    JOBS_KEY = 'jobs'
    LOGGER = getLogger('STORE_LOGGER')
    LOGGER.setLevel(INFO)
    LOGGER.addHandler(RedisHandler(REDIS))

    def __init__(self, session_id):
        self.session_id = session_id
        self.uids_key = 'uids:{}'.format(session_id)
        self.cases_key = 'cases:{}'.format(session_id)
        self.texts_key = 'texts:{}'.format(session_id)
        self.summaries_key = 'summaries:{}'.format(session_id)

    @staticmethod
    def getlogentry(follow):
        if follow:
            return Store.REDIS.blpop('log', 0)[1]
        else:
            return Store.REDIS.lpop('log')
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

    def solutions_getall(self):
        solutions = Store.REDIS.hgetall(self.solutions_key)
        return dict((name, loads(solutions_list)) for name, solutions_list in solutions.items())

    def compilations_clean(self):
        Store.REDIS.delete(self.compilations_key)

    def compilations_add(self, exercise_name, compiler_message):
        return Store.REDIS.hset(self.compilations_key, exercise_name, compiler_message)

    def compilations_getall(self):
        return Store.REDIS.hgetall(self.compilations_key)

    def results_clean(self):
        Store.REDIS.delete(self.results_key)

    def results_add(self, exercise_name, results):
        list_of_results = results.to_list_of_dicts(('input', 'args', 'expected'))
        Store.REDIS.hset(self.results_key, exercise_name, dumps(list_of_results))
        return len(list_of_results)

    def results_getall(self):
        results = Store.REDIS.hgetall(self.results_key)
        return dict((name, TestCases.from_list_of_dicts(loads(results_list))) for name, results_list in results.items())

    def cases_clean(self):
        Store.REDIS.delete(self.summaries_key)

    def summary_clean(self):
        Store.REDIS.hdel(self.summaries_key, self.uid)

    def summary_add(self, summary):
        Store.REDIS.hset(self.summaries_key, self.uid, dumps({'timestamp': self.timestamp, 'summary': summary}))
