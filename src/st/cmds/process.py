from argparse import ArgumentParser

from st.harvest import process
from st.store import Store

def main():
    parser = ArgumentParser(prog = 'st process')
    parser.add_argument('--num_workers', '-w', help = 'The number of workers.', required = True, type = int)
    parser.add_argument('--nuke', '-N', default = False, help = 'Whether to nuke previous staged jobs.', action = 'store_true')
    args = parser.parse_args()

    process(args.num_workers, args.nuke)
