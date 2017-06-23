from glob import glob
import io
from multiprocessing import Process
from os.path import join, basename, isdir
import re
from time import sleep

from sf import DEFAULT_ENCODING
from sf.solution import autodetect_solution

from st import tar2tmpdir, rmrotree, ts2iso, LOGGER
from st.store import Store

UID_TIMESTAMP_RE = re.compile( r'.*/(?P<uid>.+)/(?P<timestamp>[0-9]+)\.tar' )

def process(store, num_workers = 1):

    def worker():
        store.logger.info('Worker started')
        while True:
            job = store.jobs_dequeue()
            if job is None: break
            add(store, **job)

    processes = [Process(target = worker) for _ in range(num_workers)]
    for p in processes: p.start()
    try:
        while True: sleep(10)
    except KeyboardInterrupt:
        store.logger.info('Got KeyboardInterrupt, stopping workers')
        for p in processes: store.jobs_poison()
        for p in processes: p.join()
        store.logger.info('All workers threads have been joined')

def stage(store, path, clean = False):
    m = UID_TIMESTAMP_RE.match(path)
    if not m: return
    gd = m.groupdict()
    with open(path, 'rb') as t: tar_data = t.read()
    store.jobs_enqueue(gd['uid'], gd['timestamp'], tar_data, clean)
    LOGGER.info('Enqueued upload by uid {} at {}'.format(gd['uid'], ts2iso(gd['timestamp'])))

def add(store, tar_data, uid, timestamp, clean = False):

    store.set_harvest(uid, timestamp)

    if not clean and store.timestamps_contains(uid):
        store.logger.info('Skipping upload by uid {} at {}'.format(uid, ts2iso(timestamp)))
        return

    if clean:
        store.logger.info('Cleaning upload by uid {} at {}'.format(uid, ts2iso(timestamp)))
        store.timestamps_clean()
        store.solutions_clean()
        store.compilations_clean()
        store.results_clean()

    temp_dir = tar2tmpdir(tar_data)
    store.logger.info('Processing upload by uid {} at {} (in {})'.format(uid, ts2iso(timestamp), temp_dir))

    for exercise_path in glob(join(temp_dir, '*')):
        exercise_name = basename(exercise_path)

        solution = autodetect_solution(exercise_path)
        if solution.sources is None:
            store.logger.warn('No solutions found for exercise {}'.format(exercise_name))
            continue
        list_of_solutions = []
        for solution_name in solution.sources:
            solution_path = join(exercise_path, solution_name)
            with io.open(solution_path, 'r', encoding = DEFAULT_ENCODING) as tf: solution_content = tf.read()
            list_of_solutions.append({'name': solution_name, 'content': solution_content})
        n = store.solutions_add(exercise_name, list_of_solutions)
        store.logger.info('Imported {} solution(s) for exercise {}'.format(n, exercise_name))

        compiler_message = ''
        if solution.main_source is None:
            compiler_message = u'Missing (or ambiguous) solution'
            store.logger.warn('Missing (or ambiguous) solution for {}'.format(exercise_name))
        compilation_result = solution.compile()
        if compilation_result.returncode:
            compiler_message = compilation_result.stderr.decode(DEFAULT_ENCODING)
            store.logger.warn( 'Failed to compile exercise {}'.format(exercise_name))
        store.compilations_add(exercise_name, compiler_message)

        if compiler_message: continue
        store.logger.info( 'Compiled solution for exercise {}'.format(exercise_name))
        cases = store.cases_get(exercise_name)
        n = cases.fill_actual(solution)
        store.logger.info( 'Run {} test cases for {}'.format(n, exercise_name))
        store.cases_add(exercise_name, cases, ('input', 'args', 'expected'))

    rmrotree(temp_dir)
    store.timestamps_add()

def scan(harvests_path, session_id, clean = False):
    harvest_path = join(harvests_path, session_id)
    if not isdir(harvest_path): raise IOError('{} is not a directory'.format(harvest_path))
    LOGGER.info('Processing session {} uploads'.format(session_id))
    store = Store(session_id)
    for path in glob(join(harvest_path, '*', '[0-9]*.tar')):
        stage(store, path, clean)
