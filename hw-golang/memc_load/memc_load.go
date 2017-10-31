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
	"sync"
	"strings"
	"time"

	"github.com/akosourov/memc_load/appsinstalled"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
)

// socket read/write timeout for memcache clients
const sockTimeOut = 200 * time.Millisecond

type config struct {
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

type statistics struct {
	processed int   // all processed lines
	errors    int
	success   int
}

func (st *statistics) inc(stNew statistics) {
	st.processed += stNew.processed
	st.errors += stNew.errors
	st.success += stNew.success
}

func NewConfigParse() *config {
	cfg := new(config)
	flag.IntVar(&cfg.workers, "workers", 3, "Number of workers")
	flag.IntVar(&cfg.mcworkers, "mcworkers", 6, "Number of memcache workers")
	flag.IntVar(&cfg.jobslen, "jobslen", 100, "Length of jobs (task) queue")
	flag.IntVar(&cfg.mcjobslen, "mcjobslen", 100, "Length of memcache jobs queue")
	flag.IntVar(&cfg.maxconn, "maxconn", 4, "Length of jobs (task) queue")
	flag.StringVar(&cfg.logfile, "log", "", "Output log to file")
	flag.StringVar(&cfg.pattern, "pattern", "./test_data/*.tsv.gz", "File pattern to process")
	flag.StringVar(&cfg.idfa, "idfa", "127.0.0.1:33013", "host:port to idfa memcached")
	flag.StringVar(&cfg.gaid, "gaid", "127.0.0.1:33014", "host:port to gaid memcached")
	flag.StringVar(&cfg.adid, "adid", "127.0.0.1:33015", "host:port to adid memcached")
	flag.StringVar(&cfg.dvid, "dvid", "127.0.0.1:33016", "host:port to dvid memcached")
	flag.Parse()
	return cfg
}

// creates map of device type and correspond memcache client
func NewMapClients(cfg *config) *map[string]*memcache.Client {
	mcs := map[string]*memcache.Client{}
	mcs["idfa"] = newMClient(cfg.idfa, cfg.maxconn)
	mcs["gaid"] = newMClient(cfg.gaid, cfg.maxconn)
	mcs["adid"] = newMClient(cfg.adid, cfg.maxconn)
	mcs["dvid"] = newMClient(cfg.dvid, cfg.maxconn)
	return &mcs
}

func newMClient(addr string, maxconn int) *memcache.Client {
	mc := memcache.New(addr)
	mc.Timeout = sockTimeOut
	mc.MaxIdleConns = maxconn
	return mc
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
	pattern, err := absPath(pattern)
	if err != nil {
		return nil, err
	}

	filenames, err := filepath.Glob(pattern)
	if err != nil {
		return nil, err
	}
	sort.Strings(filenames)
	return filenames, nil
}

func dotRename(fn string) error {
	dir, f := filepath.Split(fn)
	return os.Rename(fn, dir + "." + f)
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

// worker reads gzip file and produces tasks
func fileWorker(fn string, psJobs chan<- string, wg *sync.WaitGroup) {
	defer wg.Done()
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
		psJobs <- line
	}
	if err := scanner.Err(); err != nil {
		log.Printf("Scanner error: %v", err)
		return
	}
}

// worker parses text line and produces tasks with protobuff msg
func psWorker(jobs <-chan string, mcJobs chan<- mcJob, statCh chan<- statistics, mcs map[string]*memcache.Client) {
	// process line until channel closed
	stat := statistics{}
	for line := range jobs {
		stat.processed++
		ual, err := parseUserAppsLine(line)
		if err != nil {
			log.Printf("Couldn't parse line: %v", err)
			stat.errors++
			continue
		}

		mc, ok := mcs[ual.devType]
		if !ok {
			log.Printf("Unknown device ID - %v", ual.devID)
			stat.errors++
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
			stat.errors++
			continue
		}

		// send work to mc workers
		key := fmt.Sprintf("%s:%s", ual.devType, ual.devID)
		mcJobs <- mcJob{mc, key, &msgb}
	}
	statCh <- stat
}

// worker sets data to memcache
func mcWorker(jobs <-chan mcJob, statCh chan<- statistics) {
	stat := statistics{}
	for job := range jobs {
		item := &memcache.Item{Key: job.key, Value: *job.msgb}
		if err := job.mc.Set(item); err != nil {
			log.Printf("Couldn't set to memcached: %v", err)
			stat.errors++
			continue
		}
		stat.success++
	}
	statCh <- stat
}

func main() {
	cfg := NewConfigParse()
	log.Printf("Memc loader started with options %+v", cfg)
	if cfg.logfile != "" {
		f, err := os.OpenFile(cfg.logfile, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
		if err != nil {
			log.Fatalf("Could't open logfile: %v", err)
		}
		defer f.Close()
		log.SetOutput(f)
	}

	mcs := NewMapClients(cfg)
	psJobs := make(chan string, cfg.jobslen)
	psStat := make(chan statistics)
	mcJobs := make(chan mcJob, cfg.mcjobslen)
	mcStat := make(chan statistics)
	for i := 0; i < cfg.workers; i++ {
		go psWorker(psJobs, mcJobs, psStat, *mcs)
	}
	for i := 0; i < cfg.mcworkers; i++ {
		go mcWorker(mcJobs, mcStat)
	}

	// read files
	filenames, err := getFilenames(cfg.pattern)
	if err != nil {
		log.Fatalf("Couldn't get list of files: %v", err)
	}

	wg := sync.WaitGroup{}
	log.Printf("Main: begin make tasks from files...")
	for _, fn := range filenames {
		wg.Add(1)
		go fileWorker(fn, psJobs, &wg)
	}
	wg.Wait()
	close(psJobs) // say to process workers, that tasks have been finished
	log.Print("Main: end make tasks. Wait process workers...")

	statTotal := statistics{}
	for i := 0; i < cfg.workers; i++ {
		stat := <- psStat
		statTotal.inc(stat)
	}

	close(mcJobs)  // say to memcache workers
	log.Printf("Main: Process workers done. Wait memcache workers...")
	for i := 0; i < cfg.mcworkers; i++ {
		stat := <- mcStat
		statTotal.inc(stat)
	}

	// Mark sorted files
	for _, fn := range filenames {
		if err := dotRename(fn); err != nil {
			log.Printf("Couldn't rename file - %s: %v", fn, err)
		}
	}

	log.Printf("Main: All tasks done! All: %d, Success: %d, Errors: %d",
		statTotal.processed,
		statTotal.success,
		statTotal.errors)
}
