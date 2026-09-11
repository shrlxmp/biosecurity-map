import json, io, base64, hashlib, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

orgs = json.load(io.open('orgs.json', encoding='utf-8'))
UA = {'User-Agent':'Mozilla/5.0 (favicon collector for a static data visualisation)'}

def domain(u):
    try:
        n = urllib.parse.urlparse(u).netloc.lower()
        return n[4:] if n.startswith('www.') else n
    except Exception:
        return ''

def grab(d, sz=64):
    url = 'https://www.google.com/s2/favicons?sz=%d&domain=%s' % (sz, d)
    try:
        r = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(r, timeout=25) as f:
            b = f.read()
        return b if b and len(b) > 90 else None
    except Exception:
        return None

# fingerprint the generic fallback icon so we can treat it as "no logo"
blanks = set()
for junk in ('no-such-domain-zzq1x.invalid','definitely-not-real-4821.test'):
    b = grab(junk)
    if b: blanks.add(hashlib.md5(b).hexdigest())
print('fallback fingerprints:', len(blanks))

doms = sorted({domain(o['url']) for o in orgs if domain(o['url'])})
print('unique domains:', len(doms))

res = {}
def work(d):
    b = grab(d)
    if b is None: b = grab(d, 32)
    res[d] = b
with ThreadPoolExecutor(max_workers=16) as ex:
    list(ex.map(work, doms))

logos, missing = {}, []
for d in doms:
    b = res.get(d)
    if not b or hashlib.md5(b).hexdigest() in blanks:
        missing.append(d); continue
    logos[d] = 'data:image/png;base64,' + base64.b64encode(b).decode('ascii')

json.dump(logos, io.open('logos.json','w',encoding='utf-8'))
print('logos captured: %d / %d domains' % (len(logos), len(doms)))
print('payload KB:', round(sum(len(v) for v in logos.values())/1024))
covered = sum(1 for o in orgs if logos.get(domain(o['url'])))
print('orgs with a logo: %d / %d' % (covered, len(orgs)))
print('no logo:', len(missing))
