from base64 import decodebytes
from glob import glob
import io
from json import dumps, loads
from os.path import join, basename, dirname, splitext

from sf import DEFAULT_ENCODING
from sf.testcases import TestCases

from st import tar2tmpdir, rmrotree, LOGGER
from st.store import Store

TEXTS_GLOB = '*.md'

def add(path, session_id):

    config = {}
    with open(path, 'r') as f: exec(f.read(), config)
    LOGGER.info('Read session {} configuration'.format(session_id))

    store = Store(session_id)

    n = store.uids_addall(config['REGISTERED_UIDS'].items())
    LOGGER.info('Imported {} uid(s)'.format(n))

    temp_dir = tar2tmpdir(decodebytes(config['TAR_DATA'].encode('utf-8')))

    for exercise_path in glob(join(temp_dir, '*')):

        exercise_name = basename(exercise_path)
        exercise_cases = TestCases(exercise_path)
        if len(exercise_cases) == 0:
            LOGGER.warn('Missing cases for {}'.format(exercise_name))
        else:
            n = store.cases_add(exercise_name, exercise_cases)
            LOGGER.info('Imported {} case(s) for exercise {}'.format(n, exercise_name))

        list_of_texts = []
        for text_path in glob(join(exercise_path, TEXTS_GLOB)):
            text_name = splitext(basename(text_path))[0]
            with io.open(text_path, 'r', encoding = DEFAULT_ENCODING) as tf: text = tf.read()
            list_of_texts.append({'name': text_name, 'content': text})
        if not list_of_texts:
            LOGGER.warn('Missing texts for {}'.format(exercise_name))
        else:
            n = store.texts_add(exercise_name, list_of_texts)
            LOGGER.info('Imported {} text(s) for exercise {}'.format(n, exercise_name))

    store.sessions_add(config['SECRET_KEY'])
    rmrotree(temp_dir)
