from argparse import ArgumentParser, FileType
from json import loads, dumps

from st.store import Store

def main():
    parser = ArgumentParser(prog = 'st summary')
    parser.add_argument('--session_id', '-s', help = 'The session identifier.', required = True)
    args = parser.parse_args()

    store = Store(args.session_id)
    exercises = dict((name, len(cases)) for name, cases in store.cases_getall().items())

    for uid_record in store.uids_getall():

        timestamp = store.set_harvest(uid_record['uid'])
        if timestamp is None: continue
        compilations = store.compilations_getall()
        results = store.results_getall()

        summary = {}
        for exercise, n in exercises.items():
            if exercise not in compilations: continue
            if compilations[exercise]:
                summary[exercise]= {'compile': False}
                continue
            errors = len([1 for case in results[exercise].values() if case.errors is not None])
            diffs = len([1 for case in results[exercise].values() if case.diffs is not None])
            oks = n - errors - diffs
            summary[exercise] = {'compile': True, 'errors': errors, 'diffs': diffs, 'oks': oks}

        store.summaries_add(summary)
