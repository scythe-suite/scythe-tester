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

def process(num_workers = 1):

    def worker():
        Store.LOGGER.info('Worker started')
        while True:
            job = Store.jobs_dequeue()
            if job is None: break
            add(**job)

    processes = [Process(target = worker) for _ in range(num_workers)]
    for p in processes: p.start()
    try:
        while True: sleep(10)
    except KeyboardInterrupt:
        Store.LOGGER.info('Got KeyboardInterrupt')
        for p in processes: p.join()
        Store.LOGGER.info('All workers threads have been joined')


def scan(harvests_path, session_id, clean = False):
    harvest_path = join(harvests_path, session_id)
    if not isdir(harvest_path): raise IOError('{} is not a directory'.format(harvest_path))
    LOGGER.info('Processing session {}'.format(session_id))
    for path in glob(join(harvest_path, '*', '[0-9]*.tar')):
        stage(session_id, path, clean)


def stage(session_id, path, clean = False):
    m = UID_TIMESTAMP_RE.match(path)
    if not m: return
    gd = m.groupdict()
    with open(path, 'rb') as t: tar_data = t.read()
    Store.jobs_enqueue(session_id, gd['uid'], gd['timestamp'], tar_data, clean)
    LOGGER.info('Staged harvest by uid {} at {}'.format(gd['uid'], ts2iso(gd['timestamp'])))


def add(session_id, tar_data, uid, timestamp, clean = False):

    store = Store(session_id)
    store.set_harvest(uid, timestamp)

    if not clean and store.timestamps_contained():
        Store.LOGGER.info('Skipping upload by uid {} at {} of {}'.format(uid, ts2iso(timestamp), session_id))
        return

    if clean:
        Store.LOGGER.info('Cleaning upload by uid {} at {} of {}'.format(uid, ts2iso(timestamp), session_id))
        store.timestamps_clean()
        store.solutions_clean()
        store.compilations_clean()
        store.results_clean()
        store.summary_clean()

    temp_dir = tar2tmpdir(tar_data)
    Store.LOGGER.info('Processing upload by uid {} at {} (in {})'.format(uid, ts2iso(timestamp), temp_dir))

    summary = []
    for exercise_path in glob(join(temp_dir, '*')):
        exercise_name = basename(exercise_path)

        solution = autodetect_solution(exercise_path)
        if solution.sources is None:
            Store.LOGGER.warn('No solutions found for exercise {}'.format(exercise_name))
            continue
        list_of_solutions = []
        for solution_name in solution.sources:
            solution_path = join(exercise_path, solution_name)
            with io.open(solution_path, 'r', encoding = DEFAULT_ENCODING) as tf: solution_content = tf.read()
            list_of_solutions.append({'name': solution_name, 'content': solution_content})
        n = store.solutions_add(exercise_name, list_of_solutions)
        Store.LOGGER.info('Imported {} solution(s) for exercise {}'.format(n, exercise_name))

        compiler_message = ''
        if solution.main_source is None:
            compiler_message = u'Missing (or ambiguous) solution'
            Store.LOGGER.warn('Missing (or ambiguous) solution for {}'.format(exercise_name))
        else:
            compilation_result = solution.compile()
            if compilation_result.returncode:
                compiler_message = compilation_result.stderr.decode(DEFAULT_ENCODING)
                Store.LOGGER.warn( 'Failed to compile exercise {}'.format(exercise_name))
        store.compilations_add(exercise_name, compiler_message)

        if compiler_message:
            summary.append({'name': exercise_name, 'compile': False})
            continue
        Store.LOGGER.info( 'Compiled solution for exercise {}'.format(exercise_name))
        cases = store.cases_get(exercise_name)
        n = cases.fill_actual(solution)
        Store.LOGGER.info( 'Run {} test cases for {}'.format(n, exercise_name))
        store.results_add(exercise_name, cases)

        errors = len([1 for case in cases.values() if case.errors is not None])
        diffs = len([1 for case in cases.values() if case.diffs is not None])
        ok = n - errors - diffs
        summary.append({'name': exercise_name, 'compile': True, 'errors': errors, 'diffs': diffs, 'ok': ok})

    store.summary_add(summary)
    rmrotree(temp_dir)
    store.timestamps_add()
