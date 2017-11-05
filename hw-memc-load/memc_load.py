import argparse
from collections import defaultdict
import glob
import gzip
import logging
import threading
import memcache
import multiprocessing
from Queue import Queue

from memc_load_single import parse_appsinstalled, dot_rename, prototest
import appsinstalled_pb2


MEMC_SOCKET_TIMEOUT = 1.5
MEMC_CHUNK_SIZE = 1000
TASK_DONE_MSG = None


def memc_thread(addr, job_queue, stats_queue, dry):
    mc = memcache.Client([addr], socket_timeout=MEMC_SOCKET_TIMEOUT)
    success = errors = 0
    while True:
        job = job_queue.get()
        if job == TASK_DONE_MSG:
            job_queue.task_done()
            break

        if not dry:
            notset_keys = mc.set_multi(dict(job))
            if notset_keys:
                logging.info("Couldn't set keys")
                errors += len(notset_keys)
            else:
                success += len(job)
        job_queue.task_done()
    stats_queue.put((success, errors))


# executes in single process and produces threads for io tasks
def process_file_worker((fn, memc_addr, dry)):
    # make jobs queues for every thread and run threads
    queues = defaultdict(Queue)
    stat_queue = Queue()
    for memc_name, addr in memc_addr.items():
        mc_thread = threading.Thread(target=memc_thread,
                                     args=(addr, queues[memc_name], stat_queue, dry),
                                     name=memc_name)
        mc_thread.daemon = True
        mc_thread.start()

    # process file and produce job for memcache threads
    k = 0
    chunks = defaultdict(list)
    processed = errors = 0
    logging.info('Processing %s' % fn)
    with gzip.open(fn) as fd:
        for line in fd:
            line = line.strip()
            if not line:
                continue
            processed += 1

            apps_line = parse_appsinstalled(line)
            if not apps_line:
                errors += 1
                continue

            # get appropriate job queue
            memc_name = apps_line.dev_type
            job_queue = queues.get(memc_name)
            if not job_queue:
                errors += 1
                continue

            # make proto msg
            apps_proto = appsinstalled_pb2.UserApps()
            apps_proto.lat = apps_line.lat
            apps_proto.lon = apps_line.lon
            apps_proto.apps.extend(apps_line.apps)

            # send job
            key = "%s:%s" % (apps_line.dev_type, apps_line.dev_id)
            msg = apps_proto.SerializeToString()
            job = (key, msg)
            chunks[memc_name].append(job)
            if len(chunks[memc_name]) == MEMC_CHUNK_SIZE:
                job_queue.put(chunks[memc_name])
                chunks[memc_name] = []
                k += 1
                logging.info("%s : Processed lines: %d", fn, MEMC_CHUNK_SIZE * k)

    # process rest in chunks
    for memc_name, jobs in chunks.items():
        queues[memc_name].put(jobs)

    # notify all threads that tasks done and wait them
    for _, q in queues.items():
        q.put(TASK_DONE_MSG)
        q.join()

    # collect statistics
    success = 0
    for _ in queues:
        stat = stat_queue.get()
        s, err = stat
        success += s
        errors += err

    logging.info('File %s processed. Lines: %d, success: %d, errors: %d',
                 fn, processed, success, errors)

    return fn, processed, success, errors


def main(options):
    memc_addr = {
        'idfa': options.idfa,
        'gaid': options.gaid,
        'adid': options.adid,
        'dvid': options.dvid,
    }

    worker_args = ((fn, memc_addr, options.dry)
                   for fn in glob.iglob(options.pattern))

    # older files process first
    worker_args = sorted(worker_args, key=lambda x: x[0])

    workers_pool = multiprocessing.Pool(options.workers)
    processed = success = errors = 0
    for res in workers_pool.imap(process_file_worker, worker_args):
        fn, p, s, e = res
        logging.info('Process %s done. Processed: %d, success: %d, errors: %d',
                     fn, p, s, e)
        processed += p
        success += s
        errors += e
        dot_rename(fn)

    logging.info('All done.  Processed: %d, success: %d, errors: %d',
                 processed, success, errors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parallel memcache loader')
    parser.add_argument('-w', '--workers', type=int, action='store', default=2)
    parser.add_argument('-t', '--test', action='store_true', default=False)
    parser.add_argument('-l', '--log', action='store', default=None)
    parser.add_argument('--dry', action='store_true', default=False)
    parser.add_argument('--pattern', action='store', default='./test_data/*.tsv.gz')
    parser.add_argument('--idfa', action='store', default='127.0.0.1:33013')
    parser.add_argument('--gaid', action='store', default='127.0.0.1:33014')
    parser.add_argument('--adid', action='store', default='127.0.0.1:33015')
    parser.add_argument('--dvid', action='store', default='127.0.0.1:33016')
    options = parser.parse_args()

    logging.basicConfig(
        filename=options.log,
        level=logging.INFO if not options.dry else logging.DEBUG,
        format='%(process)d|%(threadName)s [%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')

    logging.info('Memcache loader starting with options: %s', options)

    if options.test:
        prototest()
        exit(0)

    try:
        main(options)
    except Exception as e:
        logging.exception('Unexpected exception %s', e)
        exit(1)
