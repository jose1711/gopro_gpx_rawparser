#!/usr/bin/env python3
'''
Extremely simple extractor of GPS tracks from GoPro video files. Unlike
properly written parsers this one could work for some corrupted files too
and you should in fact use it only when all the other parsers failed.

- accepts any GoPro5+ video (GoPro5 tested only) with embedded gpx track
- only searches for GPS5 and GPSU labels (location, speed and timestamp)
- always assumes fixed scale
- prints csv-like output to console

output can be converted to gpx using gpsbabel:
    gpsbabel -t -i unicsv -f myoutput.csv -x track,trk2seg -o gpx -F -


reimplemented from gpmf.py/mapillary_tools (github.com/mapillary)
'''

from struct import unpack
from itertools import islice
from re import finditer
from datetime import datetime
import sys

if len(sys.argv) != 2:
    print('Usage: {} filename.mp4'.format(sys.argv[0]))
    sys.exit(1)

f = open(sys.argv[1], 'rb')


def read_chunks(file_object, chunk_size=1024*1024):
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        if b'GPS5' in data or b'GPSU' in data:
            yield [file_object.tell() - chunk_size + x.start() for x in
                   finditer(b'GPS5|GPSU', data)]
        if len(data) >= chunk_size:
            file_object.seek(f.tell() - 3)
        else:
            break


tme = '1970/01/01,00:00:00'
print('lat,lon,ele,spd,date,time')
for positions in read_chunks(f):
    for position in positions:
        f.seek(position)
        label = f.read(4)
        desc = f.read(4)
        if b'GPS5' in label:
            val_size = unpack('>b', bytes([desc[1]]))[0]
            num_values = unpack('>h', bytes([desc[2], desc[3]]))[0]
            data_to_read = num_values * val_size
            data = f.read(data_to_read)
            if val_size != 20:
                print('bad val_size at offset {}'.format(f.tell()), file=sys.stderr)
                continue
            it = iter(data)
            for i in range(num_values):
                entry = islice(it, 0, val_size)
                lat, lon, alt, spd, s3d = unpack('>lllll', bytearray(entry))
                lat /= 10000000
                lon /= 10000000
                alt /= 1000
                spd /= 1000
                print('{},{},{},{},{}'.format(*[lat, lon, alt, spd, tme]))
        else:
            timestamp = f.read(12)
            try:
                timestamp = datetime.strptime(timestamp.decode(), '%y%m%d%H%M%S')
            except ValueError:
                continue
            tme = timestamp.strftime('%Y/%m/%d,%H:%M:%S')
