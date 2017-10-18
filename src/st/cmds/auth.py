from argparse import ArgumentParser, FileType

from st.store import Store

def main():
    parser = ArgumentParser(prog = 'st auth')
    parser.add_argument('--session_id', '-s', help = 'The session identifier.', required = True)
    parser.add_argument('realms', help = 'The realms to authorize.', nargs = '+')
    args = parser.parse_args()

    store = Store(args.session_id)
    print store.sessions_dumps(args.realms)
