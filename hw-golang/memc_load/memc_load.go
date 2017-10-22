package main

import (
	"bufio"
	"compress/gzip"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync/atomic"
	"time"

	"github.com/akosourov/memc_load/appsinstalled"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
)

type (
	config struct {
		dry     bool
		workers int
		jobslen int
		logfile string
		pattern string
		idfa    string
		gaid    string
		adid    string
		dvid    string
	}

	userAppsLine struct {
		devType string
		devID   string
		lat     float64
		lon     float64
		apps    []uint32
	}
)

// socket read/write timeout for memcache client
const sockTimeOut = 200 * time.Millisecond

var (
	cfg              = config{}
	processed uint64 = 0
	errors    uint64 = 0
)

func init() {
	flag.BoolVar(&cfg.dry, "dry", false, "Dry run")
	flag.IntVar(&cfg.workers, "workers", 1, "Number of workers")
	flag.IntVar(&cfg.jobslen, "jobslen", 100, "Length of jobs (task) queue")
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
	jobs := make(chan string, 1000)
	done := make(chan bool, cfg.workers)
	for i := 0; i < cfg.workers; i++ {
		go doJob(jobs, done, *mcs, cfg.dry)
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

	for _, fn := range filenames {
		// gunzip file
		log.Printf("Processing file: %v", fn)
		f, err := os.Open(fn)
		if err != nil {
			log.Printf("Couldn't open file: %v", err)
			continue
		}
		reader, err := gzip.NewReader(f)
		if err != nil {
			log.Printf("Couldn't make reader: %v", err)
		}

		scanner := bufio.NewScanner(reader)
		for scanner.Scan() {
			line := scanner.Text()
			jobs <- line
		}
		if err := scanner.Err(); err != nil {
			log.Printf("Scanner error: %v", err)
		}

		reader.Close()
		f.Close()
		if err := dotRename(fn); err != nil {
			log.Printf("Could't rename file: %v", err)
		}
	}

	log.Printf("Main: close job channel and wait...")
	close(jobs) // say to goroutines, that tasks have been finished
	for x := 0; x < cfg.workers; x++ {
		<-done // wait all workers until they do
	}
	log.Printf("Main: All tasks done! Processed: %d, Errors: %d", processed, errors)
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
		mc.MaxIdleConns = cfg.workers + 1
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

func doJob(jobs <-chan string, done chan<- bool, mcs map[string]*memcache.Client, dryRun bool) {
	for {
		line, ok := <-jobs
		if !ok {
			// channel was closed. All jobs was done
			log.Printf("Channel was closed")
			done <- true
			return
		}

		ual, err := parseUserAppsLine(line)
		if err != nil {
			log.Printf("Couldn't parse line: %v", err)
			atomic.AddUint64(&errors, 1)
			continue
		}

		mc, ok := mcs[ual.devType]
		if !ok {
			log.Printf("Unknown device ID - %v", ual.devID)
			atomic.AddUint64(&errors, 1)
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
			atomic.AddUint64(&errors, 1)
			continue
		}

		if !dryRun {
			key := fmt.Sprintf("%s:%s", ual.devType, ual.devID)
			if err := mc.Set(&memcache.Item{Key: key, Value: msgb}); err != nil {
				log.Printf("Couldn't set to memcached: %v", err)
				atomic.AddUint64(&errors, 1)
				continue
			}
		}
		atomic.AddUint64(&processed, 1)
	}
}

func parseUserAppsLine(line string) (*userAppsLine, error) {
	line = strings.Trim(line, "")
	unpacked := strings.Split(line, "\t")
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
