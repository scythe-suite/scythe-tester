from argparse import ArgumentParser

from st.harvest import process
from st.store import Store

def main():
    parser = ArgumentParser(prog = 'st process')
    parser.add_argument('--num_workers', '-w', help = 'The number of workers.', required = True, type = int)
    parser.add_argument('--clean', '-c', default = False, help = 'Whether to clean previous staged jobs.', action = 'store_true')
    args = parser.parse_args()

    if args.clean: Store.jobs_clean()
    process(args.num_workers)
