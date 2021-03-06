from glob import glob
from multiprocessing import Process
from os.path import join, basename, isdir
import re
from time import sleep

from sf import DEFAULT_ENCODING
from sf.solution import autodetect_solution

from st import tar2tmpdir, rmrotree, ts2iso, LOGGER
from st.store import Store

UID_TIMESTAMP_RE = re.compile(r'.*/(?P<uid>.+)/(?P<timestamp>[0-9]+)\.tar')

def process(num_workers = 1, nuke = False):

    def worker():
        Store.LOGGER.info('Worker started')
        while True:
            job = Store.jobs_dequeue()
            if job is None: break
            try:
                add(**job)
            except Exception as e:
                Store.LOGGER.critical('Got an unexpected error: "{}" while processing {}/{}@{}'.format(e, job['session_id'], job['uid'], job['timestamp']) )
            Store.LOGGER.info('Done {}/{}@{}'.format(job['session_id'], job['uid'], job['timestamp']) )

    if nuke:
        Store.jobs_nuke()
        Store.LOGGER.info('Nuked old jobs')

    processes = [Process(target = worker) for _ in range(num_workers)]
    for p in processes: p.start()
    try:
        while True:
            sleep(10)
            Store.LOGGER.info('Number of queued jobs: {}'.format(Store.jobs_num()))
    except KeyboardInterrupt:
        Store.LOGGER.info('Got KeyboardInterrupt')
        for p in processes: p.join()
        Store.LOGGER.info('All workers threads have been joined')


def scan(harvests_path, session_id, watch = False):
    if not isdir(harvests_path): raise IOError('{} is not a directory'.format(harvests_path))
    seen = set()
    try:
        while True:
            LOGGER.info('Processing session {}'.format(session_id))
            for path in sorted(glob(join(harvests_path, '*', '[0-9]*.tar')), key = lambda _: _.split('/')[-1]):
                if not path in seen:
                    stage(session_id, path)
                    seen.add(path)
                else:
                    LOGGER.info('Already seen {}'.format(path))
            if not watch: break
            sleep(10)
    except KeyboardInterrupt:
        Store.LOGGER.info('Got KeyboardInterrupt, stopped watching')


def stage(session_id, path):
    m = UID_TIMESTAMP_RE.match(path)
    if not m:
        LOGGER.info('Ignoring {} (seems not to be an harvest)'.format(path))
        return
    gd = m.groupdict()
    with open(path, 'rb') as t: tar_data = t.read()
    Store.jobs_enqueue(session_id, gd['uid'], gd['timestamp'], tar_data)
    LOGGER.info('Staged harvest by uid {} at {}'.format(gd['uid'], ts2iso(gd['timestamp'])))


def add(session_id, tar_data, uid, timestamp):

    store = Store(session_id)
    store.set_harvest(uid, timestamp)

    if store.timestamps_contained():
        Store.LOGGER.info('Skipping upload by uid {} at {} of {}'.format(uid, ts2iso(timestamp), session_id))
        return

    temp_dir = tar2tmpdir(tar_data)
    Store.LOGGER.info('Processing upload by uid {} at {} (in {})'.format(uid, ts2iso(timestamp), temp_dir))

    summary = {}
    all_cases = store.cases_getall()
    for exercise_path in glob(join(temp_dir, '*')):

        exercise_name = basename(exercise_path)
        try:
            cases = all_cases[exercise_name]
        except KeyError:
            Store.LOGGER.warn('No cases found for exercise {}'.format(exercise_name))
            continue

        solution = autodetect_solution(exercise_path, True)
        if solution.sources is None:
            Store.LOGGER.warn('No sources found for exercise {}'.format(exercise_name))
            continue
        if solution.main_source is None:
            Store.LOGGER.warn('No main source for {}'.format(exercise_name))
        if solution.run_command is None:
            Store.LOGGER.warn('No runnable for {}'.format(exercise_name))
        list_of_solutions = []
        for solution_name in solution.sources:
            solution_path = join(exercise_path, solution_name)
            with open(solution_path, 'r', encoding = DEFAULT_ENCODING, errors = 'ignore') as tf: solution_content = tf.read()
            list_of_solutions.append({'name': solution_name, 'content': solution_content})
        n = store.solutions_add(exercise_name, list_of_solutions)
        Store.LOGGER.info('Imported {} solution(s) for exercise {}'.format(n, exercise_name))

        compilation_result = solution.compile()
        if compilation_result.returncode:
            compiler_message = compilation_result.stderr
            Store.LOGGER.warn( 'Failed to compile exercise {}'.format(exercise_name))
        else:
            compiler_message = ''
        store.compilations_add(exercise_name, compiler_message)

        if compiler_message:
            summary[exercise_name] = {'compile': False}
            continue
        Store.LOGGER.info( 'Compiled solution for exercise {}'.format(exercise_name))

        n = cases.fill_actual(solution)
        Store.LOGGER.info( 'Run {} test cases for {}'.format(n, exercise_name))
        store.results_add(exercise_name, cases)

        errors = len([1 for case in cases.values() if case.errors is not None])
        diffs = len([1 for case in cases.values() if case.diffs is not None])
        oks = n - errors - diffs
        summary[exercise_name] = {'compile': True, 'errors': errors, 'diffs': diffs, 'oks': oks}

    store.summaries_add(summary)
    rmrotree(temp_dir)
    store.timestamps_add()
