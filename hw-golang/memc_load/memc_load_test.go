package main

import (
	"strings"
	"testing"

	"github.com/akosourov/memc_load/appsinstalled"
	"github.com/golang/protobuf/proto"
)

func TestProto(t *testing.T) {
	sample := "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
	for _, line := range strings.Split(sample, "\n") {
		ual, err := parseUserAppsLine(line)
		if err != nil {
			t.Error(err)
		}

		ua := appsinstalled.UserApps{
			Apps: ual.apps,
			Lat:  &ual.lat,
			Lon:  &ual.lon,
		}

		data, err := proto.Marshal(&ua)
		if err != nil {
			t.Error(err)
		}

		ua2 := appsinstalled.UserApps{}
		err = proto.Unmarshal(data, &ua2)
		if err != nil {
			t.Error(err)
		}

		if *ua.Lat != *ua2.Lat || *ua.Lon != *ua2.Lon {
			t.Errorf("ua: %+v, ua2: %+v", ua, ua2)
		}
		if len(ua.Apps) != len(ua.Apps) {
			t.Error("Len of Apps are not equal")
		}
		for i, app := range ua.Apps {
			if app != ua2.Apps[i] {
				t.Errorf("Apps are not equal\n %+v \n %+v", ua.Apps, ua2.Apps)
			}
		}
	}
}
