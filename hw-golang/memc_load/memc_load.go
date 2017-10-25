package main

import (
	"bufio"
	"compress/gzip"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/akosourov/memc_load/appsinstalled"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
)

type config struct {
	dry       bool
	workers   int
	mcworkers int
	jobslen   int
	mcjobslen int
	maxconn   int
	logfile   string
	pattern   string
	idfa      string
	gaid      string
	adid      string
	dvid      string
}

type userAppsLine struct {
	devType string
	devID   string
	lat     float64
	lon     float64
	apps    []uint32
}

type mcJob struct {
	mc     *memcache.Client
	key    string
	msgb   *[]byte
}

// socket read/write timeout for memcache clients
const sockTimeOut = 200 * time.Millisecond

var (
	cfg               = config{}
	processed  uint64 = 0
	procErrors uint64 = 0
)

func init() {
	flag.IntVar(&cfg.workers, "workers", 3, "Number of workers")
	flag.IntVar(&cfg.mcworkers, "mcworkers", 6, "Number of memcache workers")
	flag.IntVar(&cfg.jobslen, "jobslen", 100, "Length of jobs (task) queue")
	flag.IntVar(&cfg.mcjobslen, "mcjobslen", 300, "Length of memcache jobs queue")
	flag.IntVar(&cfg.maxconn, "maxconn", cfg.mcworkers+1, "Length of jobs (task) queue")
	flag.StringVar(&cfg.logfile, "log", "", "Output log to file")
	flag.StringVar(&cfg.pattern, "pattern", "./test_data/*.tsv.gz", "File pattern to process")
	flag.StringVar(&cfg.idfa, "idfa", "127.0.0.1:33013", "host:port to idfa memcached")
	flag.StringVar(&cfg.gaid, "gaid", "127.0.0.1:33014", "host:port to gaid memcached")
	flag.StringVar(&cfg.adid, "adid", "127.0.0.1:33015", "host:port to adid memcached")
	flag.StringVar(&cfg.dvid, "dvid", "127.0.0.1:33016", "host:port to dvid memcached")
	flag.Parse()
}

func main() {
	log.Printf("Memc loader started with options %+v", cfg)
	if cfg.logfile != "" {
		f, err := os.OpenFile(cfg.logfile, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
		if err != nil {
			log.Fatalf("Could't open logfile: %v", err)
		}
		defer f.Close()
		log.SetOutput(f)
	}

	mcs := createMemcClients(cfg)
	jobs := make(chan string, cfg.jobslen)
	mcJobs := make(chan mcJob, cfg.mcjobslen)
	psWG := sync.WaitGroup{}   // process workers
	mcWG := sync.WaitGroup{}   // memcache workers
	for i := 0; i < cfg.workers; i++ {
		psWG.Add(1)
		go psWorker(jobs, mcJobs, *mcs, &psWG)
	}
	for j := 0; j < cfg.mcworkers; j++ {
		mcWG.Add(1)
		go mcWorker(mcJobs, &mcWG)
	}

	// read files
	pattern, err := absPath(cfg.pattern)
	if err != nil {
		log.Fatalf("Couldn't make abs path from pattern: %v", err)
	}

	filenames, err := getFilenames(pattern)
	if err != nil {
		log.Fatalf("Couldn't get list of files: %v", err)
	}

	filesWG := sync.WaitGroup{}
	for _, fn := range filenames {
		filesWG.Add(1)
		go func(fn string, wg *sync.WaitGroup) {
			defer filesWG.Done()

			log.Printf("Processing file: %v", fn)
			f, err := os.Open(fn)
			defer f.Close()
			if err != nil {
				log.Printf("Couldn't open file: %v", err)
				return
			}

			reader, err := gzip.NewReader(f)
			defer reader.Close()
			if err != nil {
				log.Printf("Couldn't make reader: %v", err)
				return
			}

			scanner := bufio.NewScanner(reader)
			for scanner.Scan() {
				line := scanner.Text()
				jobs <- line
			}
			if err := scanner.Err(); err != nil {
				log.Printf("Scanner error: %v", err)
				return
			}

			if err := dotRename(fn); err != nil {
				log.Printf("Could't rename file: %v", err)
			}
		}(fn, &filesWG)
	}

	log.Printf("Main: making tasks from files...")
	filesWG.Wait()

	log.Printf("Main: close job channel and wait process workers")
	close(jobs) // say to goroutines, that tasks have been finished
	psWG.Wait()

	log.Printf("Main: close job channel and wait memcache workers")
	close(mcJobs)
	mcWG.Wait()
	log.Printf("Main: All tasks done! Processed: %d, Errors: %d", processed, procErrors)
}

// creates map of device type and correspond memcache client
func createMemcClients(cfg config) *map[string]*memcache.Client {
	mcs := map[string]*memcache.Client{}
	devTypeMemcAddr := map[string]string{
		"idfa": cfg.idfa,
		"gaid": cfg.gaid,
		"adid": cfg.adid,
		"dvid": cfg.dvid,
	}
	for dtype, addr := range devTypeMemcAddr {
		mc := memcache.New(addr)
		mc.Timeout = sockTimeOut
		mc.MaxIdleConns = cfg.maxconn
		mcs[dtype] = mc
	}
	return &mcs
}

// makes absolute path from relative path pattern
func absPath(raw string) (string, error) {
	absp := raw
	if strings.HasPrefix(raw, ".") {
		wd, err := os.Getwd()
		if err != nil {
			return "", err
		}
		absp = filepath.Join(wd, strings.TrimLeft(raw, "."))
	}
	return absp, nil
}

// return name of files that match pattern with date order
// e.x. 20171230000000, 20171230000100, ...
func getFilenames(pattern string) ([]string, error) {
	filenames, err := filepath.Glob(pattern)
	if err != nil {
		return nil, err
	}
	sort.Strings(filenames)
	return filenames, nil
}

// worker parses text line and produces tasks with protobuff msg
func psWorker(jobs <-chan string, mcJobs chan<- mcJob, mcs map[string]*memcache.Client, wg *sync.WaitGroup) {
	// process line until channel closed
	for line := range jobs {
		ual, err := parseUserAppsLine(line)
		if err != nil {
			log.Printf("Couldn't parse line: %v", err)
			atomic.AddUint64(&procErrors, 1)
			continue
		}

		mc, ok := mcs[ual.devType]
		if !ok {
			log.Printf("Unknown device ID - %v", ual.devID)
			atomic.AddUint64(&procErrors, 1)
			continue
		}

		uap := appsinstalled.UserApps{
			Apps: ual.apps,
			Lat:  &ual.lat,
			Lon:  &ual.lon,
		}
		msgb, err := proto.Marshal(&uap)
		if err != nil {
			log.Printf("Could'n marshal uap: %v", err)
			atomic.AddUint64(&procErrors, 1)
			continue
		}

		// send work to mc workers
		key := fmt.Sprintf("%s:%s", ual.devType, ual.devID)
		mcJobs <- mcJob{mc, key, &msgb}
	}
	wg.Done()
}

// worker sets data to memcache
func mcWorker(jobs <-chan mcJob, wg *sync.WaitGroup) {
	for job := range jobs {
		item := &memcache.Item{Key: job.key, Value: *job.msgb}
		if err := job.mc.Set(item); err != nil {
			log.Printf("Couldn't set to memcached: %v", err)
			atomic.AddUint64(&procErrors, 1)
			continue
		}
		atomic.AddUint64(&processed, 1)
	}
	wg.Done()
}


func parseUserAppsLine(line string) (*userAppsLine, error) {
	line = strings.Trim(line, "")
	unpacked := strings.Split(line, "\t")
	if len(unpacked) != 5 {
		return nil, errors.New("Bad line: " + line)
	}
	devType, devID, rawLat, rawLon, rawApps := unpacked[0], unpacked[1], unpacked[2], unpacked[3], unpacked[4]
	lat, err := strconv.ParseFloat(rawLat, 64)
	if err != nil {
		return nil, err
	}
	lon, err := strconv.ParseFloat(rawLon, 64)
	if err != nil {
		return nil, err
	}
	apps := []uint32{}
	for _, rawApp := range strings.Split(rawApps, ",") {
		if app, err := strconv.ParseUint(rawApp, 10, 32); err == nil {
			apps = append(apps, uint32(app))
		}
	}

	ual := userAppsLine{
		devType: devType,
		devID:   devID,
		lat:     lat,
		lon:     lon,
		apps:    apps,
	}
	return &ual, nil
}

func dotRename(fn string) error {
	dir, f := filepath.Split(fn)
	return os.Rename(fn, dir+"."+f)
}
