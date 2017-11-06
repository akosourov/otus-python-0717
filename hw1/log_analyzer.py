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


def log_is_gzip(fn_log):
    _, gz_part = log_pattern.search(fn_log).groups()
    return gz_part is not None


def extract_gzip(fn_gz_path):
    fn_plain_path = fn_gz_path.rstrip('.gz')
    with gzip.open(fn_gz_path, 'rb') as f_in, \
            open(fn_plain_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    return fn_plain_path


def parse_log(fn_log):
    url_stat = defaultdict(lambda: {"rows": [], "stat": {}})
    size = 100000
    with open(fn_log) as f:
        i = 0
        c = 0
        for line in f:
            row = map(''.join, re.findall(r'\"(.*?)\"|\[(.*?)\]|(\S+)', line))
            try:
                url = row[4].split(' ')[1]   # GET /req?a=1
            except IndexError:
                url = row[4]                 # "0"

            url_stat[url]["rows"].append(row)

            i += 1
            if i == size:
                c += 1
                i = 0
                print "Rows processed ", c * size
    return url_stat


def calculate_stat(url_stat):
    total_time_sum = 0
    total_count = 0
    for url, data in url_stat.items():
        # count
        count = len(data["rows"])
        data["stat"]["count"] = count
        total_count += count

        # time
        time_sum = 0
        time_max = 0
        for row in data["rows"]:
            time = float(row[12])
            time_sum += time
            if time > time_max:
                time_max = time
        data["stat"]["time_sum"] = time_sum
        data["stat"]["time_max"] = time_max
        data["stat"]["time_avg"] = time_sum / count
        total_time_sum += time_sum

        # url
        data["stat"]["url"] = url

    for url, data in url_stat.items():
        data["stat"]["time_perc"] = (
            (data["stat"]["time_sum"] / total_time_sum) * 100
        )
        data["stat"]["count_perc"] = (
            (data["stat"]["count"] / total_count) * 100
        )
        data["stat"]["time_med"] = (
            (data["stat"]["time_sum"] / total_time_sum) * 100
        )


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
    if log_is_gzip(fn_log):
        print "Extract log ", fn_log_path
        fn_log_path = extract_gzip(fn_log_path)

    print "Analyze ", fn_log_path

    url_stat = parse_log(fn_log_path)

    calculate_stat(url_stat)

    # generate statistics list
    url_stat_list = [url_stat[url]["stat"] for url in url_stat]
    url_stat_list.sort(key=lambda x: -x["time_sum"])

    fn_report = get_report_name_for_log(fn_log)
    print 'Generate report ', fn_report
    fn_report_path = os.path.join(config["REPORT_DIR"], fn_report)
    generate_report(config["REPORT_TPL"], fn_report_path, url_stat_list)
    print 'Done'


if __name__ == "__main__":
    test_get_last_log()
    main()
