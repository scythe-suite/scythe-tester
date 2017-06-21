from argparse import ArgumentParser
from multiprocessing import Process

from rq import Worker

from st import redis

def main():
    parser = ArgumentParser(prog = 'scythe start')
    parser.add_argument('--num_workers', '-w', help = 'The number of workers.', required = True, type = int)
    parser.add_argument('--clean', '-c', default = False, help = 'Whether to clean previous rq status.', action = 'store_true')
    args = parser.parse_args()

    if args.clean:
        for key in redis.keys('rq*'): redis.delete(key)

    processes = []
    for n in range(args.num_workers):
        worker = Worker('default', name = 'Scythe-worker-{}'.format(n), connection = redis)
        p = Process(target = worker.work, kwargs = {'logging_level': 'WARNING'})
        p.start()
        processes.append(p)
    for p in processes: p.join()
