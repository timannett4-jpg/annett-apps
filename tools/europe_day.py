"""Print one day of the Europe trip as compact JSON, read from the installable page's own data.
usage: python3 tools/europe_day.py YYYY-MM-DD
Used by the scheduled "Europe trip: evening brief" task, so the brief always matches the app."""
import sys, re, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    date = sys.argv[1]
    page = open(os.path.join(ROOT, 'europe.html'), encoding='utf8').read()
    m = re.search(r'<script id="tripdata" type="application/json">(.*?)</script>', page, re.S)
    d = json.loads(m.group(1))
    day = next((x for x in d['days'] if x['date'] == date), None)
    if not day:
        print(json.dumps({'date': date, 'error': 'not a day of the trip'}))
        return 1
    stay = next((x for x in d.get('stays', []) if x['inn'] <= date < x['out']), None)
    leg = next((x for x in d.get('travel', []) if x['date'] == date), None)
    out = {
        'date': date,
        'day': '%s %s' % (day['dow'], day['label']),
        'dayNumber': d['days'].index(day) + 1,
        'of': len(d['days']),
        'city': day['cityName'],
        'title': day['title'],
        'times': [{'t': s['t'], 'what': s['w'], 'detail': (s.get('d') or '')[:200]} for s in day.get('slots', [])],
        'take': day.get('take') or [],
        'warnings': [w['txt'] for w in d.get('warnings', []) if w['date'] == date],
        'moving': ('%s, %s' % (leg['leg'], leg['svc'])) if leg else '',
        'sleeping': stay['name'] if stay and not stay.get('unknown') else day.get('bed', ''),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
