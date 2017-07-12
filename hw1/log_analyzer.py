#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import gzip
import shutil


# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def main():
    log_files = os.listdir(config["LOG_DIR"])
    log_filename = get_last_log(log_files)
    if log_filename is None:
        print "Нет логов для анализа"
        exit()

    if log_was_analyzed(log_filename):
        print "Лог {} уже проанализирован".format(log_filename)
        exit()

    if log_filename.endswith('.gz'):
        print "Распаковка ", log_filename
        log_filename = extract_gzip(os.path.join(config["LOG_DIR"], log_filename),
                                    os.path.join(config["LOG_DIR"], log_filename[:-3]))

    print "Обрабатывается лог ", log_filename

    # Парсим лог
    url_stat = parse_log(os.path.join(config["LOG_DIR"], log_filename))

    # Расчет статистики
    calculate_stat(url_stat)

    # list должен содержать ссылки на url_stat.values()
    # Поэтому не должно содержать много доп. памяти
    url_stat_list = [url_stat[url]["stat"] for url in url_stat]
    url_stat_list.sort(key=lambda x: -x["time_sum"])

    # Создание отчета
    date = log_filename.split('-')[3]
    report_filename = "report-{}.{}.{}.html".format(date[:4], date[4:6], date[6:8])
    print "Генерируем отчет", report_filename
    make_report(report_filename, url_stat_list)

    mark_log_done(log_filename)


def get_last_log(logs):
    def filename_keys(filename):
        # todo следует использовать re
        # date
        part = filename.split('-')[3]
        if filename.endswith('.gz'):
            date = part[:len(part)-3]
        else:
            date = part

        isfile = part.isdigit()
        return date, isfile

    logs.sort(key=filename_keys, reverse=True)
    return logs[0] if logs else None


def log_was_analyzed(log):
    with open('last_log_done.txt') as f:
        if f.readline() == log:
            return True
    return False


def extract_gzip(filename, out):
    with gzip.open(filename, 'rb') as f_in, \
            open(out, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    return os.path.basename(filename.replace('.gz', ''))


def parse_log(log):
    url_stat = {}
    with open(log) as f:
        i = 0
        c = 0
        for line in f:
            # Регулярка не моя, стоит разобраться
            row = map(''.join, re.findall(r'\"(.*?)\"|\[(.*?)\]|(\S+)', line))
            try:
                url = row[4].split(' ')[1]   # GET /req?a=1
            except IndexError:
                url = row[4]                 # "0"

            if url in url_stat:
                url_stat[url]["rows"].append(row)
            else:
                url_stat[url] = {
                    "rows": [row],
                    "stat": {}    # понадобиться позднее
                }
            i += 1
            # if i == 1234:
            #     break
            if i == 100000:
                c += 100000
                i = 0
                print "Обработано строк", c
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

    # Перцентили
    for url, data in url_stat.items():
        data["stat"]["time_perc"] = (
            (data["stat"]["time_sum"] / total_time_sum) * 100
        )
        data["stat"]["count_perc"] = (
            (data["stat"]["count"] / total_count) * 100
        )
        data["stat"]["time_med"] = (
            0  # todo разобраться
        )


def make_report(report_filename, url_stat_list):
    report_filename_path = os.path.join(config["REPORT_DIR"], report_filename)
    # Вставка данных
    with open('report.html') as tmpl_file, \
            open(report_filename_path, 'w') as report_file:
        for line in tmpl_file:
            if '$table_json' in line:
                # Memory Error на моей машине при такой команде
                # line = line.replace('$table_json', str(url_stat_list))
                # report_file.write(line)

                # Вставим большой массив данных кусками
                step = len(url_stat_list) / 10
                report_file.write(line.replace('$table_json;', '['))
                for i in range(0, len(url_stat_list), step):
                    delta = len(url_stat_list) - i
                    if delta <= step:
                        # Последний шаг
                        line = str(url_stat_list[i:])
                        line = line.lstrip('[')
                        line = line.rstrip(']')
                        report_file.write(line)
                    else:
                        line = str(url_stat_list[i:i+step])
                        line = line.lstrip('[')
                        line = line.rstrip(']')
                        report_file.write(line + ',')
                report_file.write('];')
            else:
                report_file.write(line)


def mark_log_done(log):
    with open('last_log_done.txt', 'w') as f:
        f.write(log)

if __name__ == "__main__":
    main()
