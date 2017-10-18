from argparse import ArgumentParser

from st.store import Store

def main():
    parser = ArgumentParser(prog = 'st logs')
    parser.add_argument('--follow', '-f', default = False, help = 'Whether to keep waiting for new logs.', action = 'store_true')
    args = parser.parse_args()

    while True:
        record = Store.get_logentry(args.follow)
        if not record: break
        print record
