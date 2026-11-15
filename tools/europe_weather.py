"""Put one day's forecast into europe-weather.json, the file the installable Europe app reads.
usage: python3 tools/europe_weather.py DATE PLACE HI LO RAIN SKY SOURCE
  DATE    YYYY-MM-DD, the day the forecast is for
  PLACE   where it is for, as the app should show it, e.g. "Bern"
  HI LO   forecast high and low in degrees C
  RAIN    chance of rain, 0 to 100, or "-" when the source gives none
  SKY     a few plain words, e.g. "Light snow"
  SOURCE  who the forecast is from, e.g. "Open-Meteo"
Entries for days already past are dropped. Nothing is written unless every value checks out.
Used by the scheduled "Europe trip: evening brief" task."""
import sys, json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'europe-weather.json')


def fail(msg):
    print('NOT WRITTEN: ' + msg)
    sys.exit(1)


def main():
    if len(sys.argv) != 8:
        fail('expected 7 values, got %d' % (len(sys.argv) - 1))
    date, place, hi, lo, rain, sky, src = [a.strip() for a in sys.argv[1:8]]
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        fail('date is not YYYY-MM-DD')
    try:
        hi, lo = round(float(hi), 1), round(float(lo), 1)
    except ValueError:
        fail('high and low must be numbers')
    if not (-45 <= lo <= hi <= 50):
        fail('high and low out of range, or low above high')
    if rain in ('-', ''):
        rain = None
    else:
        try:
            rain = int(round(float(rain)))
        except ValueError:
            fail('chance of rain must be a number or "-"')
        if not 0 <= rain <= 100:
            fail('chance of rain must be 0 to 100')
    if not place or len(place) > 48:
        fail('place missing or too long')
    if not sky or len(sky) > 48:
        fail('sky missing or too long')
    if not src or len(src) > 32:
        fail('source missing or too long')

    try:
        cur = json.load(open(PATH, encoding='utf8'))
        days = cur.get('days') if isinstance(cur.get('days'), dict) else {}
    except Exception:
        days = {}
    now = datetime.datetime.now(datetime.timezone.utc)
    # Keep anything for yesterday (UTC) onward: the app may still be showing today.
    floor = (now - datetime.timedelta(days=1)).date().isoformat()
    days = {k: v for k, v in days.items() if k >= floor}
    stamp = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    entry = {'place': place, 'hi': hi, 'lo': lo, 'sky': sky, 'src': src, 'at': stamp}
    if rain is not None:
        entry['rain'] = rain
    days[date] = entry
    out = {'checked': stamp, 'days': dict(sorted(days.items()))}
    text = json.dumps(out, ensure_ascii=False, indent=1) + '\n'
    if len(text.encode('utf8')) > 6000:
        fail('file would be too large')
    open(PATH, 'w', encoding='utf8').write(text)
    print(text)


if __name__ == '__main__':
    main()
