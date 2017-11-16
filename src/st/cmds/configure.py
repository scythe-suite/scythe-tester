from argparse import ArgumentParser

from st.config import add

def main():
    parser = ArgumentParser(prog = 'st configure')
    parser.add_argument('--config', '-c', help = 'The path of the config file.', required = True)
    parser.add_argument('--session_id', '-s', help = 'The session identifier.', required = True)
    args = parser.parse_args()

    add(args.config, args.session_id)
