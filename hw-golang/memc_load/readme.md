#### test_data for memcache
```
$> ls -lh test_data
total 444M
-rw-r--r-- 1 ksk ksk 148M окт 13 06:55 20170929000000.tsv.gz
-rw-r--r-- 1 ksk ksk 148M окт 13 07:10 20170929000100.tsv.gz
-rw-r--r-- 1 ksk ksk 148M окт 13 07:16 20170929000200.tsv.gz
```

#### single thread mode
```
$> time ./memc_load -workers=1 -jobslen=1
real    6m12,708s
user    4m13,084s
sys     3m8,788s
```

#### concurrent mode
```
$> time ./memc_load -workers=4 -jobslen=100
real    1m35,125s
user    2m24,276s
sys     1m6,888s
```
