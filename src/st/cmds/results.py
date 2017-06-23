from argparse import ArgumentParser, FileType
from json import loads, dumps

from st.store import Store

from tm.mkconf import read_uids

def main():
    parser = ArgumentParser(prog = 'st results')
    parser.add_argument('--session_id', '-s', help = 'The session identifier.', required = True)
    parser.add_argument('--restrict-uids-file', '-R', help = 'The UIDs to include in the results file, as a tab-separated file (default: all).')
    parser.add_argument('--results', '-r', help = 'The file where to store the json summary of the results', type = FileType('wb'), required = True)
    args = parser.parse_args()

    store = Store(args.session_id)

    if args.restrict_uids_file:
        restricted_uids = frozenset(read_uids(args.restrict_uids_file))
    else:
        restricted_uids = None

    cases = {}
    for exercise_name, exercise_cases in store.cases_getall().items():
        cases[exercise_name] = dict((name, case.to_dict()) for name, case in exercise_cases.items())

    old_results = []
    for uid_record in store.uids_getall():
        uid = uid_record['uid']
        if restricted_uids and uid not in restricted_uids: continue

        del uid_record['status']
        old_result = {'signature': uid_record}

        store.set_harvest(uid, -1)
        timestamp = store.timestamps_last()
        if not timestamp: continue
        store.set_harvest(uid, timestamp)

        solutions = store.solutions_getall()
        compilations = store.compilations_getall()
        results = store.results_getall()

        exercises = []
        for exercise_name, sources in solutions.items():
            exercise = {}
            exercise['name'] = exercise_name
            exercise['sources'] = sources
            exercise['cases'] = [{
                "diffs": None,
                "errors": compilations[exercise_name],
                "actual": None,
                "name": "<COMPILE>",
                "args": None,
                "expected": None,
                "input": None
            }]
            if exercise_name in results:
                for case_name, result in results[exercise_name].items():
                    case = result.to_dict()
                    case.update(cases[exercise_name][case_name])
                    exercise['cases'].append(case)
            exercises.append(exercise)

        old_result['exercises'] = exercises
        old_results.append(old_result)

    args.results.write(dumps(old_results, sort_keys = True, indent = 4, separators = (',', ': ')))
    args.results.close()
