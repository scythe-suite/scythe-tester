from argparse import ArgumentParser

from st.store import Store
from st.harvest import process

def main():
    parser = ArgumentParser(prog = 'st process')
    parser.add_argument('--session_id', '-s', help = 'The session identifier.', required = True)
    parser.add_argument('--num_workers', '-w', help = 'The number of workers.', required = True, type = int)
    parser.add_argument('--clean', '-c', default = False, help = 'Whether to clean previous staged jobs.', action = 'store_true')
    args = parser.parse_args()

    store = Store(args.session_id)
    if args.clean: store.jobs_clean()
    process(store, args.num_workers)
