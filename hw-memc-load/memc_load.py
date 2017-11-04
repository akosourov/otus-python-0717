import os
from collections import defaultdict
import glob
import threading
import multiprocessing
import logging
import gzip
from Queue import Queue
import memcache

from memc_load_single import parse_appsinstalled, dot_rename
import appsinstalled_pb2


MEMC_SOCKET_TIMEOUT = 1
CHUNK_SIZE = 1000
TASK_DONE_MSG = None


def memc_thread(addr, job_queue, stats_queue):
    mc = memcache.Client([addr], socket_timeout=MEMC_SOCKET_TIMEOUT)
    success = errors = 0
    while True:
        job = job_queue.get()
        if job == TASK_DONE_MSG:
            job_queue.task_done()
            break

        notset_keys = mc.set_multi(dict(job))
        # todo retry, true statistics
        if notset_keys:
            logging.info("Couldn't set keys")
            errors += len(notset_keys)
        else:
            success += len(job)
        job_queue.task_done()
    stats_queue.put((success, errors))


# executes in single process and produces threads for io tasks
def process_file_worker((fn, memc_addr)):
    # make jobs queues for every thread and run threads
    queues = defaultdict(Queue)
    stat_queue = Queue()
    for memc_name, addr in memc_addr.items():
        mc_thread = threading.Thread(target=memc_thread,
                                     args=(addr, queues[memc_name], stat_queue),
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
            if len(chunks[memc_name]) == CHUNK_SIZE:
                job_queue.put(chunks[memc_name])
                chunks[memc_name] = []
                k += 1
                logging.info("%s : Processed lines: %d", fn, CHUNK_SIZE*k)

    # rest in chunks
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


def main(options):
    memc_addr = {
        'idfa': options['idfa'],
        'gaid': options['gaid'],
        'adid': options['adid'],
        'dvid': options['dvid'],
    }

    worker_args = []
    for fn in glob.iglob(options['pattern']):
        worker_args.append((fn, memc_addr))

    workers_pool = multiprocessing.Pool(options['workers'])
    for x in workers_pool.imap(process_file_worker, worker_args):
        logging.info('x: %s', x)
    # process_file_worker("./test_data/201709290000000.tsv.gz", memc_addr)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(process)d|%(threadName)s [%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S')
    options = {
        'idfa': '127.0.0.1:33013',
        'gaid': '127.0.0.1:33014',
        'adid': '127.0.0.1:33015',
        'dvid': '127.0.0.1:33016',
        'workers': 4,
        'pattern': './test_data/*.tsv.gz'
    }
    main(options)

# def worker():
#     while True:
#         job = q.get()
#         print "PID: %d THD: %d JOB: %s" % (os.getgid(), threading._get_ident(), job)
#         q.task_done()
#
#
# q = Queue()
# print "Putting jobs"
# for i in range(30):
#     q.put("job_%d" % i)
#
# print "Starting threads"
# for _ in range(4):
#     t = threading.Thread(target=worker)
#     t.daemon = True
#     t.start()
#
# print "Wait workers"
# q.join()
