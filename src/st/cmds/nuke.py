from argparse import ArgumentParser

from st.store import Store

def main():
    parser = ArgumentParser(prog = 'st nuke')
    parser.add_argument('--session_id', '-s', help = 'The session identifier.', required = True)
    args = parser.parse_args()

    store = Store(args.session_id)
    store.nuke()
