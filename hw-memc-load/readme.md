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
$> time python memc_load_single.py
real    15m58,501s
user    11m17,532s
sys     3m41,656s
```

#### concurrent mode
```
$> time python memc_load.py -w=3
real    3m9,091s
user    8m16,556s
sys     0m14,536s
```