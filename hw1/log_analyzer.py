#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime
import gzip
import json
import os
import re
import shutil


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "REPORT_TPL": "./reports/report.html",
    "LOG_DIR": "./log"
}
log_pattern = re.compile(r'nginx-access-ui.log-([0-9]{8})(.gz)?$')


def get_last_log(dir_name):
    try:
        logs = os.listdir(dir_name)
    except OSError:
        # not exists
        return None

    if not logs:
        return None

    logs = filter(lambda x: log_pattern.search(x), logs)
    if not logs:
        return None

    def fn_keys(fn):
        match = log_pattern.search(fn)
        # match is not None, because already filtered
        date_part, gz_part = match.groups()
        date = datetime.strptime(date_part, '%Y%m%d')
        is_plain = gz_part is None
        return date, is_plain
    return max(logs, key=fn_keys)


def test_get_last_log():
    assert 'nginx-access-ui.log-20170630' == get_last_log('./test_log')


def get_report_name_for_log(fn_log):
    date_part, _ = log_pattern.search(fn_log).groups()
    date = datetime.strptime(date_part, '%Y%m%d')
    return 'report-{}.html'.format(date.strftime('%Y.%m.%d'))


def log_was_analyzed(fn):
    fn_report = get_report_name_for_log(fn)
    return os.path.isfile(os.path.join(config["REPORT_DIR"], fn_report))


def ilog_line(fn_log_path):
    _, gz_part = log_pattern.search(fn_log_path).groups()
    if gz_part:
        fd = gzip.open(fn_log_path)
    else:
        fd = open(fn_log_path)

    for line in fd:
        yield line
    fd.close()


def ilog_parsed_line(fn_log_path):
    for line in ilog_line(fn_log_path):
        row = map(''.join, re.findall(r'\"(.*?)\"|\[(.*?)\]|(\S+)', line))
        try:
            url = row[4].split(' ')[1]  # GET /req?a=1
        except IndexError:
            url = row[4]                # "0"
        try:
            time = float(row[12])
        except ValueError:
            # bad log line. Skip
            continue
        yield url, time


def median(lst):
    size = len(lst)
    if size == 0:
        return 0
    elif size % 2 == 1:
        return lst[size // 2]
    else:
        before_m = lst[(size/2) - 1]
        after_m = lst[(size/2)]
        return (before_m + after_m) / 2


def calculate_stat(fn_log_path):
    url_stat = defaultdict(lambda: {"count": 0,
                                    "count_perc": 0,
                                    "time_each": [],
                                    "time_sum": 0,
                                    "time_max": 0,
                                    "time_avg": 0,
                                    "time_med": 0,
                                    "time_perc": 0})
    total_count = 0
    total_time_sum = 0
    i = 0
    for parsed in ilog_parsed_line(fn_log_path):
        url, time = parsed
        stat = url_stat[url]
        stat["count"] += 1
        stat["time_each"].append(time)
        stat["time_sum"] += time
        if time > stat["time_max"]:
            stat["time_max"] = time
        total_count += 1
        total_time_sum += time

        i += 1
        if i % 10000 == 0:
            print 'Rows processed', i

    for stat in url_stat.values():
        stat["count_perc"] = 100 * float(stat["count"]) / total_count
        stat["time_perc"] = 100 * stat["time_sum"] / total_time_sum
        stat["time_avg"] = stat["time_sum"] / stat["count"]
        stat["time_med"] = median(stat["time_each"])
        stat.pop("time_each")   # remove unnecessary data
    return url_stat


def generate_report(tpl_path, fn_report_path, url_stat_list):
    stat_text = json.dumps(url_stat_list)
    with open(tpl_path) as tpl_file, \
            open(fn_report_path, 'w') as report_file:
        for line in tpl_file:
            if '$table_json' in line:
                line = line.replace('$table_json', stat_text)
            report_file.write(line)


def main():
    fn_log = get_last_log(config["LOG_DIR"])
    if fn_log is None:
        print "Logs not found in folder %s" % config["LOG_DIR"]
        exit()

    if log_was_analyzed(fn_log):
        print "Log %s already analyzed" % fn_log
        exit()

    fn_log_path = os.path.join(config["LOG_DIR"], fn_log)
    print "Analyze ", fn_log_path

    # read file line by line and calculate statistics
    url_stat = calculate_stat(fn_log_path)

    # generate statistics list
    for url, stat in url_stat.items():
        stat["url"] = url
    url_stat_list = url_stat.values()
    url_stat_list.sort(key=lambda x: -x["time_sum"])

    fn_report = get_report_name_for_log(fn_log)
    print 'Generate report ', fn_report
    fn_report_path = os.path.join(config["REPORT_DIR"], fn_report)
    generate_report(config["REPORT_TPL"], fn_report_path, url_stat_list)
    print 'Done'


if __name__ == "__main__":
    test_get_last_log()
    main()
