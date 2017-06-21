from argparse import ArgumentParser, FileType
from json import loads, dumps

from st import redis
from tm.mkconf import read_uids

def main():
    parser = ArgumentParser(prog = 'st log')
    parser.add_argument('--session_id', '-s', help = 'The session identifier.', required = True)
    parser.add_argument('--restrict-uids-file', '-R', help = 'The UIDs to include in the results file, as a tab-separated file (default: all).')
    parser.add_argument('--results', '-r', help = 'The file where to store the json summary of the results', type = FileType('wb'), required = True)

    args = parser.parse_args()

    if args.restrict_uids_file:
        restricted_uids = read_uids(args.restrict_uids_file)
    else:
        restricted_uids = None

    cases_key = 'cases:{}'.format(args.session_id)
    cases = {}
    for exercise_name, cases_list in redis.hgetall(cases_key).items():
        cases[exercise_name] = {}
        for case in loads(cases_list):
            cases[exercise_name][case['name']] = case

    old_results = []
    uids_key = 'uids:{}'.format(args.session_id)
    for m in redis.smembers(uids_key):

        old_result = {}
        old_result['signature'] = loads(m)
        del old_result['signature']['status']
        uid = old_result['signature']['uid']

        if restricted_uids is not None and not uid in restricted_uids: continue

        timestamps_key = 'timestamps:{}:{}'.format(args.session_id, uid)
        timestamp = redis.zrange(timestamps_key, -1, -1)
        if not timestamp: continue
        timestamp = timestamp[0]

        solutions_key = 'solutions:{}:{}'.format(uid, timestamp)
        solutions = redis.hgetall(solutions_key)

        compilations_key = 'compilations:{}:{}'.format(uid, timestamp)
        compilations = redis.hgetall(compilations_key)

        results_key = 'results:{}:{}'.format(uid, timestamp)
        results = redis.hgetall(results_key)

        exercises = []
        for solution_name, solution in solutions.items():
            exercise = {}
            exercise['name'] = solution_name
            exercise['sources'] = loads(solution)
            compilation_case = {
                "diffs": None,
                "errors": None,
                "actual": None,
                "name": "<COMPILE>",
                "args": None,
                "expected": None,
                "input": None
            }
            if solution_name in compilations:
                compilation_case['errors'] = compilations[solution_name]
            exercise_cases = []
            if solution_name in results and solution_name in cases:
                for case in loads(results[solution_name]):
                    case.update(cases[solution_name][case['name']])
                    exercise_cases.append(case)
            exercise['cases'] = exercise_cases
            exercises.append(exercise)

        old_result['exercises'] = exercises
        old_results.append(old_result)

    args.results.write(dumps(old_results, sort_keys = True, indent = 4, separators = (',', ': ')))
    args.results.close()
