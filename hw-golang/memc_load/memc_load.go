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

	"github.com/golang/protobuf/proto"
	"github.com/bradfitz/gomemcache/memcache"

	"github.com/akosourov/memc_load/appsinstalled"
)

type config struct {
	test    bool
	dry     bool
	logfile string
	pattern string
	idfa    string
	gaid    string
	adid    string
	dvid    string
}

type userAppsLine struct {
	devType string
	devID   string
	lat     float64
	lon     float64
	apps    []uint32
}

var cfg = config{}

var mcs = map[string]*memcache.Client{}

func init() {
	flag.BoolVar(&cfg.test, "t", false, "Test run")
	flag.BoolVar(&cfg.test, "test", false, "Test run")
	flag.BoolVar(&cfg.dry, "dry", false, "Dry run")
	flag.StringVar(&cfg.logfile, "log", "", "Output log to file")
	flag.StringVar(&cfg.pattern, "pattern", "/home/ksk/otus/Highload/hw-concurrent/test_data/*.tsv.gz", "File pattern to process")
	flag.StringVar(&cfg.idfa, "idfa", "127.0.0.1:33013", "host:port to idfa memcached")
	flag.StringVar(&cfg.gaid, "gaid", "127.0.0.1:33014", "host:port to gaid memcached")
	flag.StringVar(&cfg.adid, "adid", "127.0.0.1:33015", "host:port to adid memcached")
	flag.StringVar(&cfg.dvid, "dvid", "127.0.0.1:33016", "host:port to dvid memcached")
	flag.Parse()
}

func main() {
	if cfg.logfile != "" {
		f, err := os.OpenFile(cfg.logfile, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
		if err != nil {
			log.Fatalf("Could't open logfile: %v", err)
		}
		defer f.Close()
		log.SetOutput(f)
	}

	log.Printf("Memc loader started with options %+v", cfg)

	if !cfg.test {
		mainWork(cfg)
	} else {
		prototest()
	}
}

func mainWork(cfg config) {
	// read files
	filenames, err := filepath.Glob(cfg.pattern)
	if err != nil {
		log.Fatalf("Couldn't get list of files: %v", err)
	}
	sort.Strings(filenames) // older log e.x. 20171230000000 first
	log.Printf("Filenames: %v", filenames)
	for _, fn := range filenames {
		processed, errors := 0, 0
		log.Printf("Processing: %v", fn)

		// gunzip file
		f, err := os.Open(fn)
		if err != nil {
			log.Printf("Couldn't open file %v - %v", fn, err)
			continue
		}
		reader, err := gzip.NewReader(f)
		if err != nil {
			log.Printf("Couldn't make reader: %v", err)
		}

		scanner := bufio.NewScanner(reader)
		for scanner.Scan() {
			line := scanner.Text()
			ua := parseUserAppsLine(line)
			insertUserApps(cfg.idfa, ua, cfg.dry)
		}
		if err := scanner.Err(); err != nil {
			log.Printf("Scanner error: %v", err)
		}

		//fnGunzip := strings.TrimSuffix(fn, ".gz")
		//fw, err := os.Create(fnGunzip)
		//if err != nil {
		//	log.Printf("Couldn't create gunzip file: %v", err)
		//}
		//
		//n, err := io.Copy(fw, reader)
		//if err != nil {
		//	log.Printf("Couldn't copy: %v", err)
		//}
		//log.Printf("Gunziped bytes: %v", n)

		reader.Close()
		f.Close()
		//fw.Close()

		processed++
		errors++
	}
}

func prototest() {
	log.Print("Starting test proto")
	sample := "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
	for _, line := range strings.Split(sample, "\n") {
		uap := parseUserAppsLine(line)

		ua := appsinstalled.UserApps{
			Apps: uap.apps,
			Lat:  &uap.lat,
			Lon:  &uap.lon,
		}
		packed := ua.String()
		log.Printf("PB serialized: %v", packed)

		data, err := proto.Marshal(&ua)
		if err != nil {
			log.Printf("Couldn't marshal: %v", err)
		}
		log.Printf("PB data: %v, length: %v", data, len(data))

		ua2 := appsinstalled.UserApps{}
		err = proto.Unmarshal(data, &ua2)
		if err != nil {
			log.Printf("Couldn't unmarshal: %v", err)
		}

		log.Printf("ua1: %v", ua)
		log.Printf("ua2: %v", ua2)
	}
}

func parseUserAppsLine(line string) userAppsLine {
	line = strings.Trim(line, "")
	unpacked := strings.Split(line, "\t")
	devType, devID, rawLat, rawLon, rawApps := unpacked[0], unpacked[1], unpacked[2], unpacked[3], unpacked[4]
	lat, _ := strconv.ParseFloat(rawLat, 64)
	lon, _ := strconv.ParseFloat(rawLon, 64)
	apps := []uint32{}
	for _, rawApp := range strings.Split(rawApps, ",") {
		if app, err := strconv.ParseUint(rawApp, 10, 32); err == nil {
			apps = append(apps, uint32(app))
		}
	}

	ua := userAppsLine{
		devType: devType,
		devID:   devID,
		lat:     lat,
		lon:     lon,
		apps:    apps,
	}
	return ua
}

func insertUserApps(memcAddr string, ual userAppsLine, dryRun bool) {
	uap := appsinstalled.UserApps{
		Apps: ual.apps,
		Lat:  &ual.lat,
		Lon:  &ual.lon,
	}
	key := fmt.Sprintf("%s:%s", ual.devType, ual.devID)
	if dryRun {
		log.Printf("INSERT: %v - %v", key, uap.String())
	} else {
		mc, _ := mcs["idfa"]
		if mc == nil {
			mc = memcache.New(memcAddr)
			mcs["idfa"] = mc
		}

		msgb, err := proto.Marshal(&uap)
		if err != nil {
			log.Printf("Could'n marshal msg: %v", err)
		}

		log.Printf("Settting value - %v", uap.String())
		if err:= mc.Set(&memcache.Item{Key: key, Value: msgb}); err != nil {
			log.Fatalf("Couldn't set to memcached: %v", err)
		}

		item, _ := mc.Get(key)

		uaps := new(appsinstalled.UserApps)
		_ = proto.Unmarshal(item.Value, uaps)
		log.Fatalf("Got value - %v", uaps)
	}
}
