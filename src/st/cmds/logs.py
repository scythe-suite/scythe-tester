from argparse import ArgumentParser

from st.config import add

from st import redis

def main():
    parser = ArgumentParser(prog = 'st log')
    parser.add_argument('--follow', '-f', default = False, help = 'Whether to keep waiting for new logs.', action = 'store_true')

    args = parser.parse_args()

    if args.follow:
        while True:
            print redis.blpop('log', 0)[1]
    else:
        while True:
            record = redis.lpop('log')
            if not record: break
            print record
