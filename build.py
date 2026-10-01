#!/usr/bin/env python3
"""
Ranko — site builder.

  python3 build.py          -> fabrique le site dans le dossier dist/
  python3 build.py serve    -> fabrique le site puis l'ouvre sur http://localhost:8080

Les textes sont dans content/, les images dans images/, le design dans src/.
Aucun module à installer : seulement Python 3.
"""
import datetime, html, json, os, re, shlex, shutil, sys, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, 'content')
IMAGES = os.path.join(ROOT, 'images')
SRC = os.path.join(ROOT, 'src')
DIST = os.path.join(ROOT, 'dist')
SITE_URL = 'https://www.ranko.ca'
YEAR = datetime.date.today().year

esc = lambda s: html.escape(s or '', quote=True)


# ---------------------------------------------------------------- content files

def read_content(path):
    """key: value lines, then '== section' blocks."""
    meta, sections, cur = {}, {}, None
    for line in open(path, encoding='utf-8').read().splitlines():
        m = re.match(r'^==\s*(\w+)\s*$', line)
        if m:
            cur = m.group(1); sections[cur] = []; continue
        if cur is None:
            if ':' in line:
                k, v = line.split(':', 1); meta[k.strip()] = v.strip()
        else:
            sections[cur].append(line)
    return meta, {k: '\n'.join(v).strip() for k, v in sections.items()}


def paragraphs(text):
    return [p.strip() for p in re.split(r'\n\s*\n', text or '') if p.strip()]


def inline(s):
    s = esc(s)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', lambda m: f'<a href="{m.group(2)}"'
               + (' target="_blank" rel="noopener"' if m.group(2).startswith('http') else '') + f'>{m.group(1)}</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
    return s


def md(text, reveal=True):
    """Tiny markdown: #/##/###/#### headings, '- ' lists, other lines = paragraphs."""
    out, items = [], []
    r = ' data-reveal' if reveal else ''
    def flush():
        if items:
            out.append(f'<ul{r}>' + ''.join(f'<li>{inline(i)}</li>' for i in items) + '</ul>'); items.clear()
    for line in (text or '').splitlines():
        line = line.strip()
        if not line: flush(); continue
        m = re.match(r'^(#{1,4})\s+(.*)$', line)
        if line.startswith('- '): items.append(line[2:]); continue
        flush()
        if m:
            n = max(2, len(m.group(1)))  # h1 is kept for the page title
            out.append(f'<h{n}{r}>{inline(m.group(2))}</h{n}>')
        else:
            out.append(f'<p{r}>{inline(line)}</p>')
    flush()
    return '\n'.join(out)


# ---------------------------------------------------------------- images

PH = {  # placeholder families: ratio -> available widths
    '16x9': (16 / 9, [640, 1280, 1840]), '1x1': (1, [480, 960, 1440]), '4x5': (.8, [480, 960, 1440]),
    '9x16': (9 / 16, [480, 960]), '3x4': (.75, [480, 960]), '21x9': (21 / 9, [1280, 1840]),
}
SIZES = {
    'full': '(min-width: 768px) calc(100vw - 48px), calc(100vw - 32px)',
    'half': '(min-width: 768px) 50vw, 100vw',
    'third': '(min-width: 768px) 34vw, 100vw',
    'quarter': '(min-width: 768px) 25vw, 50vw',
    'cover': '(min-width: 1100px) 25vw, (min-width: 900px) 33vw, 50vw',
    'preview': '360px',
    'tile': '(min-width: 768px) 34vw, 75vw',
}
SLOTS = []  # every image slot, for IMAGES.md


def webp_size(path):
    """Width and height of a WebP file, read from its header (no module needed)."""
    with open(path, 'rb') as f:
        d = f.read(40)
    if d[12:16] == b'VP8X':
        return 1 + int.from_bytes(d[24:27], 'little'), 1 + int.from_bytes(d[27:30], 'little')
    if d[12:16] == b'VP8L':
        b0 = int.from_bytes(d[21:25], 'little')
        return (b0 & 0x3FFF) + 1, ((b0 >> 14) & 0x3FFF) + 1
    if d[12:16] == b'VP8 ':
        return int.from_bytes(d[26:28], 'little') & 0x3FFF, int.from_bytes(d[28:30], 'little') & 0x3FFF
    return None


def placeholder_family(w, h):
    r = w / h
    return min(PH, key=lambda k: abs(PH[k][0] - r))


def picture(owner, slot, w, h, alt='', size='full', eager=False, cls='', label=None, register=True):
    """An image slot. Uses images/<owner>/<slot>.webp if present, otherwise the placeholder."""
    rel = f'{owner}/{slot}.webp'
    real = os.path.exists(os.path.join(IMAGES, rel))
    if register:
        SLOTS.append((owner, slot, w, h, real))
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    style = f'aspect-ratio:{w}/{h}'
    if real:
        # a smaller copy <slot>-800.webp, when present, is used by phones
        small = os.path.join(IMAGES, owner, f'{slot}-800.webp')
        srcset = ''
        if os.path.exists(small):
            fw = (webp_size(os.path.join(IMAGES, rel)) or (w, h))[0]
            srcset = f' srcset="/images/{owner}/{slot}-800.webp 800w, /images/{rel} {fw}w" sizes="{SIZES.get(size, "100vw")}"'
        img = f'<img src="/images/{rel}"{srcset} width="{w}" height="{h}" alt="{esc(alt)}" {load}>'
        tag = ''
    else:
        fam = placeholder_family(w, h)
        ws = PH[fam][1]
        srcset = ', '.join(f'/assets/img/placeholder/{fam}-{x}.webp {x}w' for x in ws)
        img = (f'<img src="/assets/img/placeholder/{fam}-{ws[1] if len(ws) > 1 else ws[0]}.webp" srcset="{srcset}" '
               f'sizes="{SIZES.get(size, "100vw")}" width="{w}" height="{h}" alt="{esc(alt)}" {load}>')
        tag = f'<span class="ph-label">{esc(label or owner)} · {w} × {h}</span>'
    return f'<div class="media {cls}" style="{style}">{img}{tag}</div>'


def clip(owner, slot, w, h, alt, size, label):
    """Short muted looping video (MP4) hosted with the site, e.g. a former animated GIF.
    images/<owner>/<slot>.mp4 + a still images/<owner>/<slot>.webp shown until it plays."""
    mp4 = os.path.join(IMAGES, owner, slot + '.mp4')
    SLOTS.append((owner, slot + '.mp4', w, h, os.path.exists(mp4)))
    still = picture(owner, slot, w, h, alt, size, label=label)
    if not os.path.exists(mp4):
        return still
    poster = f'/images/{owner}/{slot}.webp' if os.path.exists(os.path.join(IMAGES, owner, slot + '.webp')) else ''
    video = (f'<video class="clip-v" muted loop playsinline preload="none" width="{w}" height="{h}"'
             f'{f" poster={chr(34)}{poster}{chr(34)}" if poster else ""} data-src="/images/{owner}/{slot}.mp4" aria-label="{esc(alt)}"></video>')
    return f'<figure class="clip">{still.replace("</div>", video + "</div>", 1)}</figure>'


# ---------------------------------------------------------------- vimeo

_vimeo_sizes_path = os.path.join(CONTENT, 'vimeo-sizes.json')
VIMEO = json.load(open(_vimeo_sizes_path)) if os.path.exists(_vimeo_sizes_path) else {}
_vimeo_dirty = False


def vimeo_size(vid, h=None):
    """Aspect ratio of a Vimeo video, looked up once online then remembered in content/vimeo-sizes.json."""
    global _vimeo_dirty
    if vid not in VIMEO:
        url = f'https://vimeo.com/{vid}' + (f'/{h}' if h else '')
        try:
            req = urllib.request.Request('https://vimeo.com/api/oembed.json?url=' + url, headers={'User-Agent': 'ranko-build'})
            j = json.load(urllib.request.urlopen(req, timeout=15))
            VIMEO[vid] = {'w': j['width'], 'h': j['height']}
        except Exception as e:
            print(f'  ! Vimeo {vid}: size not found ({e}), using 16:9')
            VIMEO[vid] = {'w': 16, 'h': 9}
        _vimeo_dirty = True
    return VIMEO[vid]['w'], VIMEO[vid]['h']


def vimeo(ref, mode, owner, label, size='full', caption='', eager=False, slot=None):
    """mode 'loop' = muted background loop (plays on screen); 'film' = poster + play button.
    slot: name of the cover image (default video-<id>); lets the same video appear twice with two covers."""
    vid, _, h = ref.partition('/')
    w, hh = vimeo_size(vid, h or None)
    slot = slot or f'video-{vid}'
    poster = picture(owner, slot, round(w * 100), round(hh * 100), '', size, eager, label=label, register=False) \
        .replace('class="media ', 'class="media poster ')
    # Recompute a clean poster size label (use 1920 on the long side)
    pw, ph = (1920, round(1920 * hh / w)) if w >= hh else (round(1920 * w / hh), 1920)
    poster = re.sub(r'· \d+ × \d+', f'· {pw} × {ph}', poster)
    poster = re.sub(r'width="\d+" height="\d+"', f'width="{pw}" height="{ph}"', poster)
    poster = re.sub(r'aspect-ratio:[\d/]+', f'aspect-ratio:{w}/{hh}', poster)
    SLOTS.append((owner, slot, pw, ph, os.path.exists(os.path.join(IMAGES, owner, f'{slot}.webp'))))
    btn = '' if mode == 'loop' else '<button class="play" type="button"><span>Play</span></button>'
    cap = f'<figcaption>{inline(caption)}</figcaption>' if caption else ''
    return (f'<figure class="vm vm-{mode}" data-vimeo="{vid}" data-h="{h}" data-mode="{mode}" style="--ar:{w}/{hh}">'
            f'{poster}{btn}</figure>{cap}')


# ---------------------------------------------------------------- Privacy: rows like the Services page

def legal(text):
    """Privacy: the date in small, then one row per "## " section, like the service rows:
    the title on the left (t4), its text on the right (t2), thin grey lines between the rows."""
    blocks = re.split(r'^##\s+', text or '', flags=re.M)
    intro, rows = blocks[0].strip(), []
    for b in blocks[1:]:
        title, _, body = b.partition('\n')
        rows.append(f'''<section class="sec lg-row">
  <h2 class="lg-t" data-split>{inline(title.strip())}</h2>
  <div class="lg-body" data-reveal>{md(body.strip(), reveal=False)}</div>
</section>''')
    date = f'<p class="lg-date">{inline(intro)}</p>' if intro else ''
    return date + '\n'.join(rows)


def odo_end(text, delay=0.0):
    """When the odometer of `text` started at `delay` stops rolling (to start the next one right after)."""
    digits = [int(c) for c in text if c.isdigit()]
    return delay + (len(digits) - 1) * .08 + .6 + max(digits, default=0) * .12


def odometer(text, delay=0.0):
    """A number whose digits roll up from 0 to their value when their block appears ("5.0", "38").
    Other characters (the point) stay still. Decorative: give the real value to screen readers elsewhere."""
    out, k = [], 0
    for ch in text:
        if ch.isdigit():
            n = int(ch)
            col = ''.join(f'<span>{d}</span>' for d in range(n + 1))
            out.append(f'<span class="odo" style="--n:{n};--d:{delay + k * .08:.2f}s"><span class="odo-r">{col}</span></span>')
            k += 1
        else:
            out.append(esc(ch))
    return ''.join(out)


# ---------------------------------------------------------------- Services: the process

def process(text):
    """Services, under the AI videos: the process in the same 3-column rows as the services (title · sentence · right column).
    Text: content/services.txt, section "process"."""
    paras = paragraphs(text)
    head = paras[0].splitlines() if paras else ['']
    steps = []
    for p in paras[1:]:
        m = re.match(r'^(\d+)\.\s*(.+?)\n(.+)$', p, re.S)
        if m: steps.append((m.group(1), m.group(2).strip(), ' '.join(m.group(3).split())))
    # set like the AI block of the home: the title on the left (t4), the sentence in small on the right, last lines level;
    # then the steps as tiles (grey frame, one white card per step)
    # the step number rolls from 0 up to its value (0 → 1, 0 → 1 → 2 …), like an odometer, when the tile appears
    def roll(n, i):
        digits = ''.join(f'<span>{k}</span>' for k in range(int(n) + 1))
        return (f'<span class="pr-n" style="--n:{int(n)};--i:{i}"><span class="sr">{n}</span>'
                f'<span class="pr-roll" aria-hidden="true">{digits}</span></span>')
    cards = ''.join(f'''<li class="ai-card pr-card" data-reveal>{roll(n, i)}<h3>{inline(t)}</h3><p>{inline(d).replace(" | ", "<br>")}</p></li>''' for i, (n, t, d) in enumerate(steps))
    sub = f'<p class="page-intro ai-sub" data-split>{inline(head[1]).replace(" | ", " <br>")}</p>' if len(head) > 1 else ''
    return f'''<section class="sec pr" aria-labelledby="pr-t">
  <div class="ai-hd pr-hd"><h2 id="pr-t" class="pr-t" data-split>{inline(head[0])}</h2>{sub}</div>
  <ol class="ai-frame pr-grid">{cards}</ol>
</section>'''


# ---------------------------------------------------------------- Services: one row per service, in 3 columns

def svc_row(txt):
    """Services: title on the left, the sentence in the middle (thin line on its left), the list on the right
    (like the reference Romain liked, in the Ranko style: no numbers, no colour). Phones: one under the other."""
    title = re.search(r'^##\s+(.+)$', txt, re.M)
    items = re.findall(r'^- (.+)$', txt, re.M)
    rest = [l.strip() for l in txt.splitlines() if l.strip() and not l.lstrip().startswith(('##', '- '))]
    desc = ' '.join(re.sub(r'^\*(.+)\*$', r'\1', l) for l in rest)
    lst = f'<ul class="svc3-l">{"".join(f"<li data-reveal>{inline(i)}</li>" for i in items)}</ul>' if items else '<div class="svc3-l"></div>'
    return f'''<section class="sec svc3">
  <h2 class="svc3-t" data-split>{inline(title.group(1)) if title else ""}</h2>
  <p class="svc3-d" data-reveal>{inline(desc)}</p>
  {lst}
</section>'''


# ---------------------------------------------------------------- Afterhours: mosaic

def mosaic(text, owner):
    """Afterhours: every image and video in a wall of 3 columns like the home page (widths computed in site.js so the
    columns end on the same line), each piece in its own format. A click opens it full screen (image, or the Vimeo
    video). Same content file as before: ### headings name the pieces that follow them."""
    items, group = [], ''
    for para in paragraphs(text):
        first = para.split(None, 1)[0]
        if first not in ('video', 'film', 'image', 'clip'):
            m = re.match(r'^#+\s*(.+)$', para)
            group = m.group(1).strip() if m else group
            continue
        for item in para.split(' | '):
            t = shlex.split(item.replace('’', "'"), posix=True)
            kind, ref, rest = t[0], t[1], t[2:]
            opts = dict(x.split('=', 1) for x in rest if '=' in x)
            flags = [x for x in rest if '=' not in x]
            alt = opts.get('alt', '')
            if kind == 'image':
                w, h = [int(x) for x in next((f for f in flags if re.match(r'^\d+x\d+$', f)), '1600x1600').split('x')]
                media = picture(owner, ref, w, h, alt, 'third', not items, label=group)
                data = f'data-kind="image" data-src="/images/{owner}/{ref}.webp"'
                what = alt
            else:
                vid, _, hsh = ref.partition('/')
                w, h = vimeo_size(vid, hsh or None)
                media = picture(owner, f'video-{vid}', w * 10, h * 10, '', 'third', not items, label=group, register=False)
                data = f'data-kind="{"film" if kind == "film" else "loop"}" data-vimeo="{vid}" data-h="{hsh}"'
                what = 'film' if kind == 'film' else 'video'
                if items:   # every video plays in its tile, muted, in a loop — except the very first piece (the vending machine film)
                    media = tile_video(media, ref, owner)
                else:
                    media = media.replace('</div>', '<span class="ah-play" aria-hidden="true"></span></div>', 1)
            items.append((h / w, f'''<li class="k-card" style="--order:{len(items)}"><button type="button" class="ah-open" {data} data-title="{esc(group)}" data-alt="{esc(alt)}" data-ar="{w}/{h}" aria-label="Open {esc(group)} — {esc(what)}">
  {media}
</button></li>'''))
    # 3 columns, in the page order, each piece going to the column that is the shortest so far
    cols, tall = [[], [], []], [0, 0, 0]
    for r, html_ in items:
        c = tall.index(min(tall)); cols[c].append(html_); tall[c] += r
    wall = ''.join(f'<li class="k-col"><ol>{"".join(c)}</ol></li>' for c in cols)
    return f'''<section class="sec ah-sec" aria-label="Afterhours pieces"><ol class="k-cards">{wall}</ol></section>
<dialog class="lb" aria-label="Afterhours piece">
  <div class="lb-stage"><div class="lb-media"></div></div>
  <p class="lb-cap"><span class="lb-title"></span><span class="lb-count"></span></p>
  <button type="button" class="lb-btn lb-prev" aria-label="Previous piece">←</button>
  <button type="button" class="lb-btn lb-next" aria-label="Next piece">→</button>
  <button type="button" class="lb-btn lb-close" aria-label="Close" autofocus>×</button>
</dialog>'''


# ---------------------------------------------------------------- media rows

def media_rows(text, owner, label, first_eager=False):
    out = []
    # keep a clean heading order: if the page has no '##' heading, '###' become level-2 headings
    promote = not re.search(r'^## ', text or '', re.M)
    eager = [first_eager]  # only the very first image of the page loads eagerly
    first_cell = [first_eager]
    for para in paragraphs(text):
        first = para.split(None, 1)[0]
        if first not in ('video', 'film', 'image', 'clip'):
            h = md(para)
            if promote:
                h = re.sub(r'<h3( data-reveal)?>(.*?)</h3>', r'<h2 class="h3"\1>\2</h2>', h)
            out.append(f'<div class="m-text">{h}</div>')
            continue
        cells, sizes, ratios = [], [], []
        for item in para.split(' | '):
            t = shlex.split(item.replace('’', "'"), posix=True)
            kind, ref, rest = t[0], t[1], t[2:]
            opts = dict(x.split('=', 1) for x in rest if '=' in x)
            flags = [x for x in rest if '=' not in x]
            size = next((f for f in flags if f in ('full', 'half', 'third', 'quarter')), 'full')
            dims = next((f for f in flags if re.match(r'^\d+x\d+$', f)), None)
            right = 'right' in flags
            cap = opts.get('caption', '')
            if kind == 'image':
                w, h = [int(x) for x in (dims or '1600x900').split('x')]
                # expected export size: 2x the displayed width, never more than the original
                tw = {'full': 2400, 'half': 1600, 'third': 1200, 'quarter': 900}[size]
                if w > tw: w, h = tw, round(h * tw / w)
                # "plain": a logo or cut-out on a transparent background — shown on the page, no grey behind it
                body = picture(owner, ref, w, h, opts.get('alt', ''), size, eager[0], label=label, cls='tile-media' + (' is-plain' if 'plain' in flags else ''))
                eager[0] = False
                body += f'<figcaption>{inline(cap)}</figcaption>' if cap else ''
                body = f'<figure class="img">{body}</figure>'
            elif kind == 'clip':
                w, h = [int(x) for x in (dims or '1080x1920').split('x')]
                body = clip(owner, ref, w, h, opts.get('alt', ''), size, label)
                body += f'<figcaption>{inline(cap)}</figcaption>' if cap else ''
            else:
                body = vimeo(ref, 'loop' if kind == 'video' else 'film', owner, label, size, cap, eager[0], opts.get('poster'))
                vw_, vh_ = vimeo_size(ref.partition('/')[0], ref.partition('/')[2] or None); w, h = vw_, vh_
                eager[0] = False
            if opts.get('tag'):   # tag="Before": a word in white, top left, on the picture or the video
                body = re.sub(r'<figure class="', '<figure class="has-tag ', body, count=1)
                body = body.replace('</figure>', f'<span class="m-tag">{esc(opts["tag"])}</span></figure>', 1)
            sizes.append(size); ratios.append(h / w if w else 1)
            reveal = '' if first_cell[0] else ' data-reveal'  # the first media of a page shows at once
            first_cell[0] = False
            fill = ' c-fill' if 'fill' in flags else ''  # "fill": the picture takes the whole height of its line (cropped)
            fill += ' c-desk' if 'desktop' in flags else ''
            fill += ' c-phone' if 'phone' in flags else ''
            fill += ' c-pwide' if 'phonewide' in flags else ''
            fill += ' c-p1' if 'phonefirst' in flags else (' c-p2' if 'phonesecond' in flags else (' c-plast' if 'phonelast' in flags else ''))  # phones: this piece first / second  # "phonewide": on phones this piece takes the whole width (cropped 4:5)  # "phone": the video shown inside a phone, 9:16 like the vertical videos  # "desktop": big screens only (e.g. a piece repeated to complete a line)
            cells.append(f'<div class="cell c-{size}{" c-right" if right else ""}{fill}"{reveal}>{body}</div>')
        span = sum({'full': 12, 'half': 6, 'third': 4, 'quarter': 3}[s] for s in sizes)
        if re.search(r'\bwall\b', para.split(' | ')[0]) and len(cells) > 1:
            # "wall" on the first item: it takes the left column on its own, the others are stacked on its right;
            # widths computed (site.js) so both columns end on the same line
            cols = [[cells[0]], cells[1:]]
            li = lambda c: c.replace('<div class="cell', '<li class="k-card cell', 1)[:-6] + '</li>'
            out.append('<ol class="k-cards m-wall is-lead">' + ''.join(f'<li class="k-col"><ol>{"".join(li(x) for x in c)}</ol></li>' for c in cols) + '</ol>')
        elif re.search(r'\bstrip\b', para.split(' | ')[0]):  # flag "strip": every piece on one line, equal widths
            mid = ' is-middle' if re.search(r'\bmiddle\b', para.split(' | ')[0]) else ''
            wide = ' is-wide-end' if ratios[-1] <= 1.05 else ''  # last piece square or landscape: may take the whole width on phones
            out.append(f'<div class="m-row is-strip{mid}{wide}" style="--n:{len(cells)}">{"".join(cells)}</div>')
        elif span > 12:  # too many items for one line: a wall like the home page — columns whose widths are computed
            # (site.js) so they fill the whole width and all end on the same line; each picture keeps its shape
            n = len(cells)
            ncol = 2 if n <= 3 else (4 if all(x == 'quarter' for x in sizes) and n >= 8 else 3)
            cols, tall = [[] for _ in range(ncol)], [0.0] * ncol
            for c, r in zip(cells, ratios):   # in order, each piece into the column that is the shortest so far
                k = tall.index(min(tall)); cols[k].append(c.replace('<div class="cell', '<li class="k-card cell', 1)[:-6] + '</li>'); tall[k] += r
            odd = ' is-odd' if len(cells) % 2 else ''  # phones: the last piece then takes the whole width
            odd += ' is-stack' if re.search(r'\bstack\b', para.split(' | ')[0]) else ''  # "stack": phones one under the other, each in its own format
            out.append(f'<ol class="k-cards m-wall{odd}">' + ''.join(f'<li class="k-col"><ol>{"".join(c)}</ol></li>' for c in cols) + '</ol>')
        else:   # "middle" on the first item of a line: the pieces are centred on the height of the line
            mid = ' is-middle' if re.search(r'\bmiddle\b', para.split(' | ')[0]) else ''
            out.append(f'<div class="m-row{mid}">{"".join(cells)}</div>')
    # lines of "strip" that follow each other share one box: on phones their pieces flow two by two
    # across the lines, so no line ends with an empty half
    merged = []
    for o in out:
        if o.startswith('<div class="m-row is-strip') and merged and merged[-1].startswith('<div class="m-strips">'):
            merged[-1] = merged[-1][:-6] + o + '</div>'
        elif o.startswith('<div class="m-row is-strip'):
            merged.append('<div class="m-strips">' + o + '</div>')
        else:
            merged.append(o)
    # odd number of pieces: on phones the last one takes the whole width
    merged = [m.replace('<div class="m-strips">', '<div class="m-strips is-odd">', 1)
              if m.startswith('<div class="m-strips">') and (m.count('<div class="cell ') - m.count(' c-desk"') - m.count(' c-pwide"')) % 2 else m for m in merged]
    return '\n'.join(merged)


# ---------------------------------------------------------------- layout

# RANKO logo (black paths only, coloured with the text colour)
LOGO = open(os.path.join(SRC, 'assets/brand/logo-inline.svg'), encoding='utf-8').read()
LOGO = LOGO.replace('<svg', '<svg aria-hidden="true" focusable="false"', 1)

NAV = [('/work', 'Work'), ('/services', 'Services'), ('/about', 'About'), ('/afterhours', 'Afterhours')]
MAIL = 'mailto:hello@ranko.ca?subject=Hello%20Ranko!'
# Google Analytics measurement ID ("G-XXXXXXXXXX"). Empty = no analytics and no cookie banner.
# When set, analytics only loads after the visitor clicks "Accept" (Quebec Law 25: off by default).
GA_ID = 'G-J9570DV4M6'



def css():
    s = open(os.path.join(SRC, 'assets/css/site.css'), encoding='utf-8').read()
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*([{};,>])\s*', r'\1', s)
    s = re.sub(r':\s+', ':', s)   # only after ':' — a space before ':' in a selector means "inside" (.media :is(img))
    return s.replace(';}', '}').strip()


CSS = None
HAS_LENIS = os.path.exists(os.path.join(SRC, 'assets/js/lenis.min.js'))


def ver(rel):
    """Short fingerprint of a file, added to its address so browsers pick up each new version (assets are cached a year)."""
    import hashlib
    with open(os.path.join(SRC, rel), 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


# home intro (like salient.framer.website): a dark curtain with the logo, once per visit, skipped when motion is reduced
INTRO_JS = ("<script>try{if(!sessionStorage.getItem('ranko-intro')&&!matchMedia('(prefers-reduced-motion: reduce)').matches)"
            "{document.documentElement.classList.add('intro-on');sessionStorage.setItem('ranko-intro','1')}}catch(e){}</script>")


def layout(path, title, description, body, current='', video=False, og_image='/assets/img/og-ranko.png'):
    here = ' aria-current="page"'
    nav = ''.join(f'<li><a href="{h}"{here if current == h else ""}>{t}</a></li>' for h, t in NAV)
    canonical = SITE_URL + (path if path != '/' else '/')
    ld = json.dumps({'@context': 'https://schema.org', '@type': 'Organization', 'name': 'Ranko', 'url': SITE_URL,
                     'email': 'hello@ranko.ca', 'foundingDate': '2020',
                     'address': {'@type': 'PostalAddress', 'addressLocality': 'Montreal', 'addressRegion': 'QC', 'addressCountry': 'CA'},
                     'sameAs': ['https://www.instagram.com/ranko.ca/', 'https://www.linkedin.com/company/rankoca', 'https://vimeo.com/rankoca']})
    lenis = f'<script src="/assets/js/lenis.min.js?v={ver("assets/js/lenis.min.js")}" defer></script>' if HAS_LENIS else ''
    pre = '<link rel="preconnect" href="https://player.vimeo.com">' if video else ''
    return f'''<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Ranko">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE_URL}{og_image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
{pre}
<style>{CSS}</style>
<script>document.documentElement.classList.add('js')</script>
{INTRO_JS if path == '/' else ''}
{lenis}
<script src="/assets/js/site.js?v={ver("assets/js/site.js")}" defer></script>
<script type="application/ld+json">{ld}</script>
</head>
<body>
{f'<div class="intro" aria-hidden="true"><span class="intro-logo">{LOGO}</span></div>' if path == '/' else ''}
<a class="skip" href="#main">Skip to content</a>
<header class="kn">
  <div class="kn-l">
    <a class="hd-logo" href="/" aria-label="Ranko — home">{LOGO}</a>
    <p class="kn-time">Montreal, QC <span data-clock></span></p>
  </div>
  <nav class="kn-nav" aria-label="Main"><ul>{nav}</ul></nav>
  <a class="kn-cta" href="{MAIL}">Work with us</a>
  <button class="hd-menu kn-plus" type="button" aria-expanded="false" aria-controls="menu" aria-label="Menu"><span class="kn-x" aria-hidden="true"></span></button>
</header>
<div class="menu" id="menu" hidden>
  <ul>{nav}<li><a href="{MAIL}">Contact</a></li></ul>
  <p><a href="{MAIL}">hello@ranko.ca</a></p>
</div>
<main id="main">
{body}
</main>
<div class="bottom">
{cta()}
{footer()}
</div>
{consent()}
</body>
</html>
'''


def consent():
    """Cookie banner: only when Google Analytics is set up. Analytics loads after "Accept" only (site.js)."""
    if not GA_ID:
        return ''
    return f'''<div class="consent" role="dialog" aria-label="Cookies" data-ga="{esc(GA_ID)}" hidden>
  <p>We'd like to measure visits with Google Analytics. Cookies are only used if you agree. <a href="/privacy">Privacy & cookies</a></p>
  <div class="consent-btns"><button type="button" data-consent="no">Decline</button><button type="button" data-consent="yes">Accept</button></div>
</div>'''


def cta():
    # a black tile (same as the e-mail tile of the About page): "Work with us" on top, the address at the bottom; one link.
    # Beside it, a light grey tile calling for AI talent (like the "Talent wanted" tile of losyork.tv)
    return f'''<section class="cta" aria-labelledby="cta-t">
  <a class="cta-tile" href="{MAIL}" data-reveal><h2 id="cta-t" class="cta-t">Let's take your brand<br>somewhere it's never been.</h2><span class="cta-mail">hello@ranko.ca</span></a>
  <a class="cta-jobs" href="mailto:jobs@ranko.ca?subject=AI%20talent" data-reveal><span class="cta-jobs-t">AI talent wanted</span><span>jobs@ranko.ca</span></a>
</section>'''


def footer():
    nav = ''.join(f'<li><a href="{h}">{t}</a></li>' for h, t in NAV)
    return f'''<footer class="ft">
  <div class="ft-col"><h2>Ranko</h2><ul>{nav}<li><a href="mailto:romain@ranko.ca?subject=Hello%20Ranko!">Contact</a></li></ul></div>
  <div class="ft-col"><h2>Hours</h2><p>Monday – Friday<br>9am – 6pm</p><p>—</p><p><a href="mailto:hello@ranko.ca?subject=Hello%20RANKO%20!">hello@ranko.ca</a></p></div>
  <div class="ft-col"><h2>Socials</h2><ul>
    <li><a href="https://www.instagram.com/ranko.ca/" target="_blank" rel="noopener">Instagram</a></li>
    <li><a href="https://www.linkedin.com/company/rankoca" target="_blank" rel="noopener">LinkedIn</a></li>
    <li><a href="https://vimeo.com/rankoca" target="_blank" rel="noopener">Vimeo</a></li></ul></div>
  <p class="ft-copy"><span>© All rights reserved — Ranko 2020 - {YEAR}</span>
    <a href="/privacy">Privacy & cookies</a>{' <button type="button" data-consent-open>Cookie settings</button>' if GA_ID else ''}
    <a class="ft-top" href="#main">Back to top <svg viewBox="0 0 24 24" aria-hidden="true"><path class="totop-s" d="M12 21V8.5"/><path class="totop-h" d="M12 2.5 17.6 10.6Q12 7.4 6.4 10.6Z"/></svg></a></p>
</footer>'''


# ---------------------------------------------------------------- pages

def load_projects():
    order = [l.strip() for l in open(os.path.join(CONTENT, 'work-order.txt')).read().splitlines() if l.strip()]
    projects = {}
    for slug in order:
        meta, sec = read_content(os.path.join(CONTENT, 'projects', slug + '.txt'))
        projects[slug] = dict(meta=meta, sec=sec, slug=slug)
    extra = sorted(f[:-4] for f in os.listdir(os.path.join(CONTENT, 'projects')) if f.endswith('.txt') and f[:-4] not in projects)
    for slug in extra:
        print(f'  ! content/projects/{slug}.txt is not listed in content/work-order.txt (page built, not listed)')
        meta, sec = read_content(os.path.join(CONTENT, 'projects', slug + '.txt'))
        projects[slug] = dict(meta=meta, sec=sec, slug=slug, hidden=True)
    return order, projects


def cover(p, size='cover', eager=False, register=True):
    m = p['meta']
    return picture(p['slug'], 'cover', 1200, 1500, m.get('cover_alt', ''), size, eager, 'tile-media', m['title'], register)


def tile_card(media, p):
    """Project name and role in a small frosted pill laid over the picture (same glass as the menu),
    with a white "View project" button inside it, which inverts when the tile is hovered."""
    m = p['meta']
    card = (f'<span class="tcard" aria-hidden="true"><span class="tcard-txt"><span class="tcard-name">{esc(m["title"])}</span>'
            f'<span class="tcard-role">{esc(m["role"])}</span></span>'
            '<span class="tcard-btn"><span class="tcard-btn-l">View project</span><span class="tcard-btn-i">→</span></span></span>')
    return media[:media.rindex('</div>')] + card + '</div>'


def tile_video(media, ref, owner=''):
    """A cover image with a muted loop laid over it (the image shows until the video plays).
    ref: a Vimeo id, or a video file hosted with the site in images/<owner>/."""
    if not ref:
        return media
    if ref.endswith(('.webm', '.mp4')):
        if not os.path.exists(os.path.join(IMAGES, owner, ref)):
            print(f'  ! images/{owner}/{ref} not found (tile shows its image)')
            return media
        video = f'<video class="clip-v tile-clip" muted loop playsinline preload="none" data-src="/images/{owner}/{ref}" aria-hidden="true"></video>'
        return media[:media.rindex('</div>')] + video + '</div>'
    vid, _, h = ref.partition('/')
    w, hh = vimeo_size(vid, h or None)
    fig = f'<figure class="vm vm-loop tile-vm" data-vimeo="{vid}" data-h="{h}" data-mode="loop" style="--ar:{w}/{hh}" aria-hidden="true"></figure>'
    return media[:media.rindex('</div>')] + fig + '</div>'


def ai_bento(statement, n_brands, quotes='', tile4='', tile1=''):
    """Home, after Selected Work: the AI part as a bento (like kanso.framer.media), made only of existing material:
    the second statement as a two-tone title, the two AI videos of the Services page, Services texts, client logos."""
    head, _, tail = statement.partition(' — ')
    # like a page header: the first part as the title (black), the rest in small on the right, like "Specialized in…"
    title, sub = (inline(head), inline(tail)) if tail else (inline(statement), '')
    title = title.replace(' | ', '<br>')   # line breaks chosen by hand (| in content/home.txt)
    _, svc = read_content(os.path.join(CONTENT, 'services.txt'))
    def part(key):
        txt = svc.get(key, '')
        t = re.search(r'^##\s+(.+)$', txt, re.M); tag = re.search(r'^\*(.+)\*\s*$', txt, re.M)
        body = ' '.join(l.strip() for l in txt.splitlines() if l.strip() and not l.lstrip().startswith(('#', '-', '*')))
        return (t.group(1) if t else ''), (tag.group(1) if tag else body), re.findall(r'^- (.+)$', txt, re.M)
    films_t, films_d, films_l = part('films')
    sys_t, sys_d, sys_l = part('systems')
    ai_t, ai_d, _ = part('ai')
    intro = svc.get('intro', '').replace(' | ', ' ').split('. ')[0].strip().rstrip('.') + '.'
    # tile 4: the end of the AI text of the Services page ("…the idea doesn't get scaled down to fit, …")
    m = re.search(r'the idea .+', ai_d)
    tall_txt = (m.group(0)[0].upper() + m.group(0)[1:]) if m else ai_d
    tall_txt = tile4 or tall_txt   # the sentence chosen in content/home.txt (ai_tile) wins
    vids = [x.split()[1] for x in re.findall(r'video \d+', svc.get('media', ''))]
    def vid_card(vid, cls, owner='services'):
        w, h = vimeo_size(vid)
        media = picture(owner, f'video-{vid}', w * 10, h * 10, '', 'third', label='AI', register=False)
        return tile_video(media, vid, owner).replace('class="media ', f'class="media {cls} ', 1)
    logos = [f for b in ('louis-vuitton', 'dior', 'mcdonald-s', 'uniqlo', 'nikon', 'jagermeister')
             for f in os.listdir(LOGOS) if f.split('.')[0] == b][:6]
    avatars = ''.join(f'<span class="ai-av"><img src="/assets/logos/{f}" alt="" class="{ {"k": "is-k", "g": "is-g", "c": "is-c"}.get(f.split(".")[1], "") if f.count(".") == 2 else ""}" loading="lazy"></span>' for f in logos)
    # tile 3: the three services as on the Services page — title, then its skills (or, for AI, its first sentence)
    feat = lambda t, d: (f'<div class="ai-card ai-feat" data-reveal>'
                             f'<h3>{inline(t)}</h3>'
                             + (f'<ul>{"".join(f"<li>{inline(x)}</li>" for x in d)}</ul>' if isinstance(d, list) else f'<p>{inline(d)}</p>')
                             + '</div>')
    # testimonials (content/home.txt, section "testimonials"): one at a time in the second card, they take turns (site.js)
    qrows = [[x.strip() for x in l.split('|')] for l in quotes.splitlines() if l.strip() and not l.lstrip().startswith('#') and l.count('|') >= 3]
    # Google Business rating ("google: 5.0 | 38" in the same section)
    g = re.search(r'^google:\s*([\d.,]+)\s*\|\s*(\d+)', quotes, re.M)
    # animated when the tile appears: the stars light up one after the other, the numbers roll up from 0 (like the process)
    stars = ''.join(f'<span class="st" style="--i:{i}"><span>★</span><span class="st-on">★</span></span>' for i in range(5))
    rating = (f'<a class="ai-rating" href="https://www.google.com/maps/search/?api=1&amp;query=Ranko+Montreal" target="_blank" rel="noopener" '
              f'aria-label="Rated {g.group(1)} out of 5 on Google, {g.group(2)} reviews"><span class="ai-stars" aria-hidden="true">{stars}</span>'
              f'<span aria-hidden="true"><b>{odometer(g.group(1), .35)}</b> · {odometer(g.group(2), odo_end(g.group(1), .35) - .2)} Google reviews</span></a>') if g else ''
    qs = ''.join(f'''<figure class="ai-q{" is-on" if i == 0 else ""}"{" hidden" if i else ""}><blockquote>“{inline(q)}”</blockquote>
        <figcaption><b>{esc(n)}</b><span>{esc(r)} — {esc(pj)}</span></figcaption></figure>''' for i, (q, n, r, pj) in enumerate(qrows))
    dots = ''.join(f'<button type="button" class="ai-dot" aria-label="Testimonial {i + 1} of {len(qrows)}" aria-pressed="{"true" if i == 0 else "false"}"></button>' for i in range(len(qrows)))
    # tile 4: the Bronco intro (WebM hosted with the site, images/home/ai-intro.webm + its still ai-intro.webp)
    tall_media = tile_video(picture('home', 'ai-intro', 1510, 2160, '', 'third', label='AI', register=False), 'ai-intro.webm', 'home') \
        .replace('class="media ', 'class="media ai-bg ', 1)
    return f'''<section class="sec ai" aria-labelledby="ai-t">
  <div class="ai-hd">
    <h2 id="ai-t" class="ai-t" data-split>{title}</h2>
    {f'<p class="page-intro ai-sub" data-split>{sub}</p>' if sub else ''}
  </div>
  <div class="ai-bento">
    <div class="ai-col ai-frame">
      <div class="ai-card ai-hero" data-reveal>{vid_card(vids[0], "ai-bg") if vids else ""}
        <p class="ai-hero-t">{inline(tile1 or ai_t)}</p>
      </div>
      <a class="k-pill ai-more" href="/work">View all work</a>
    </div>
    <div class="ai-col ai-quote" data-reveal>
      <div class="ai-top"><div class="ai-avs">{avatars}</div>{rating}</div>
      <div class="ai-quotes" aria-label="What clients say">{qs}</div>
      <div class="ai-dots" role="group" aria-label="Choose a testimonial">{dots}</div>
      <a class="k-pill ai-more" href="/about">About <em>Ranko</em></a>
    </div>
    <div class="ai-col ai-frame ai-feats">
      {feat(films_t, films_l)}
      {feat(sys_t, sys_l)}
      {feat(ai_t, ai_d.split(". ")[0].rstrip(".") + ".")}
      <a class="k-pill ai-more" href="/services">View all services</a>
    </div>
    <div class="ai-col ai-tall" data-reveal>{tall_media}
      <p class="ai-tall-b">{inline(tall_txt)}</p>
      <a class="k-pill ai-more" href="{MAIL}">Work with us</a>
    </div>
  </div>
</section>'''


def page_home(order, P):
    meta, sec = read_content(os.path.join(CONTENT, 'home.txt'))
    featured = [s.strip() for s in meta.get('featured', '').split(',') if s.strip()]
    n_brands = len([b for b in read_content(os.path.join(CONTENT, 'about.txt'))[1].get('brands', '').splitlines() if b.strip() and not b.lstrip().startswith('#')])
    # featured work: 4:5 tiles placed freely, same sizes and places as the Squarespace home page.
    # each tile: (left, top, width) in pixels measured on a 1440 px wide screen; scaled to the screen width.
    # on phones the tiles simply stack, small ones alternating left and right.
    plan = [(133, 0, 641), (963, 827, 404), (74, 1323, 582), (834, 2273, 582), (133, 2397, 404),
            (74, 3306, 522), (963, 3637, 404), (133, 4216, 404), (903, 4588, 285)]
    plan_w, plan_h = 1440, 5040
    tile_videos = dict((k.strip(), v.strip()) for k, _, v in (x.partition('=') for x in meta.get('tile_videos', '').split(',')) if v.strip())
    tiles = []
    for i, slug in enumerate(featured):
        p = P[slug]; m = p['meta']
        x, y, w = plan[i % len(plan)]
        if i >= len(plan):  # more projects than places: continue below
            y += plan_h * (i // len(plan))
        pos = f'--x:{x / plan_w * 100:.3f}%;--y:{y / plan_h * 100:.3f}%;--w:{w / plan_w * 100:.3f}%'
        media = tile_card(tile_video(cover(p, "tile", eager=i < 2, register=False), tile_videos.get(slug), slug), p)
        tiles.append(f'''<li class="ft-tile{" is-big" if w >= 500 else ""}" style="{pos}" data-reveal><a href="/{slug}" aria-label="{esc(m["title"])} — {esc(m["role"])}">
  {media}
</a></li>''')
    rows = -(-len(featured) // len(plan))
    facts = []
    for line in sec.get('facts', '').splitlines():
        if '|' not in line or line.lstrip().startswith('#'): continue
        num, suffix, text = [x.strip() for x in line.split('|', 2)]
        num = num.replace('{projects}', str(len(order))).replace('{brands}', str(n_brands))
        static = num.startswith('=')
        num = num.lstrip('=')
        count = '' if static else f' data-count="{esc(num)}"'
        facts.append(f'<li class="fact" data-reveal><span class="fact-n"><span{count}>{esc(num)}</span>{esc(suffix)}</span><span class="fact-t">{inline(text)}</span></li>')
    reel = meta.get('reel', '')
    # ---- Kanso-style home (test) ------------------------------------------------------------
    # project cards in 3 independent columns (a wall): each card sits right under the one above, always the same gap.
    # Every project keeps its weight from the current home page (widths in `plan`: Cinco widest, Louis Vuitton smallest):
    # a column is as wide as its widest project, the others take their share of it. Pictures stay 4:5.
    weight = {'jagermeister': 641, 'la-ronde-2-0': 404}   # Jägermeister as big as Cinco
    if meta.get('columns'):   # columns chosen in content/home.txt: "a, b | c, d | e"
        slots = [[x.strip() for x in c.split(',') if x.strip()] for c in meta['columns'].split('|')]
    else:
        slots = [featured[k::3] for k in range(3)]
    cols = [[(featured.index(slug), slug, weight.get(slug, plan[featured.index(slug) % len(plan)][2]))
             for slug in c if slug in featured] for c in slots]
    # every card fills its column (no holes), and the column widths are worked out so that all columns end at the
    # same height: a column with more projects is narrower. Measured on a 1440 px screen: row width 1352 px,
    # 20 px between cards, ~81 px of text under each 4:5 picture.
    W, g, m = 1352, 20, 81
    counts = [len(c) for c in cols if c]
    k = sum(1 / (1.25 * n) for n in counts)
    H = (W + sum((n * m + (n - 1) * g) / (1.25 * n) for n in counts)) / k
    widths = [(H - n * m - (n - 1) * g) / (1.25 * n) for n in counts]
    cards = []
    for col, cw in zip([c for c in cols if c], widths):
        items = []
        for i, slug, w in col:
            p = P[slug]; m_ = p['meta']
            media = tile_video(cover(p, "tile", eager=i < 3, register=False), tile_videos.get(slug), slug)
            items.append(f'''<li class="k-card" style="--order:{i}" data-reveal><a href="/{slug}">
  {media}
  <span class="k-card-meta"><span class="k-card-name">{esc(m_["title"])}</span><span class="k-card-role">{esc(m_["role"])}</span></span>
</a></li>''')
        cards.append(f'<li class="k-col" style="--grow:{cw:.1f}"><ol>{"".join(items)}</ol></li>')
    work_meta, _ = read_content(os.path.join(CONTENT, 'work.txt'))
    reel = meta.get('reel', '')
    body = f'''
<div class="k">
<section class="page-hd k-hero" aria-labelledby="hero-t">
  <h1 id="hero-t" class="page-t hero-t" data-split aria-label="Creative Company"><span aria-hidden="true">Creative<br>Company</span></h1>
  <p class="page-intro" data-split>{inline(meta.get("hero_sub", ""))}</p>
</section>

<section class="reel" aria-label="Showreel">
  <div class="reel-frame">
    {vimeo(reel, "loop", "home", "Showreel", "full", eager=True)}
  </div>
</section>

<section class="sec statement" aria-labelledby="st-t">
  <h2 id="st-t" class="big-t" data-split>{inline(sec.get("statement", "")).replace(" | ", " <br>")}</h2>
</section>

<section class="k-sec k-shelf" aria-labelledby="k-work">
  <div class="k-head">
    <h2 id="k-work" class="k-title" data-split>Selected Work</h2>
    <div class="k-side" data-reveal><a class="k-pill" href="/work">View all work</a></div>
  </div>
  <ol class="k-cards">{"".join(cards)}</ol>
</section>

{ai_bento(sec.get("statement2", ""), n_brands, sec.get("testimonials", ""), meta.get("ai_tile", ""), meta.get("ai_tile1", ""))}

</div>
'''
    return layout('/', meta.get('page_title', 'Ranko'), meta.get('description', ''), body, video=True)


def page_work(order, P):
    meta, sec = read_content(os.path.join(CONTENT, 'work.txt'))
    tiles = []
    for i, slug in enumerate(order):
        p = P[slug]; m = p['meta']
        tiles.append(f'''<li class="tile k-card" data-reveal><a href="/{slug}">
  {cover(p, eager=i < 3)}
  <span class="k-card-meta"><span class="k-card-name">{esc(m["title"])}</span><span class="k-card-role">{esc(m["role"])}</span></span>
</a></li>''')
    body = f'''
<section class="page-hd k-hero">
  <h1 class="page-t" data-split>{esc(meta.get("heading", "Our Work"))}</h1>
  <p class="page-intro" data-split>{inline(meta.get("intro", ""))}</p>
</section>
<hr class="hd-line">
<section class="sec"><ul class="grid">{"".join(tiles)}</ul></section>'''
    return layout('/work', meta['page_title'], meta['description'], body, '/work')


def pj_related(slugs, P):
    """Project pages: 2 or 3 related projects in cards (like Work), chosen in the project file ("related: a, b, c")."""
    picks = [x.strip() for x in slugs.split(',') if x.strip() in P]
    if not picks:
        return ''
    cards = ''.join(f'''<li class="tile k-card" data-reveal><a href="/{x}">
  {cover(P[x])}
  <span class="k-card-meta"><span class="k-card-name">{esc(P[x]["meta"]["title"])}</span><span class="k-card-role">{esc(P[x]["meta"]["role"])}</span></span>
</a></li>''' for x in picks)
    return f'''<section class="sec pj-related" aria-labelledby="rel-t">
  <h2 id="rel-t" class="pj-rel-t" data-split>Related projects</h2>
  <ul class="pj-rel-grid">{cards}</ul>
</section>'''


def pj_quotes(title):
    """Project pages: the client testimonials of this project (content/home.txt, section "testimonials",
    last column = project), in grey cards, two per row, after a thin line."""
    _, hs = read_content(os.path.join(CONTENT, 'home.txt'))
    rows = [[x.strip() for x in l.split('|')] for l in hs.get('testimonials', '').splitlines()
            if l.strip() and not l.lstrip().startswith('#') and l.count('|') >= 3]
    mine = [r for r in rows if title.lower().startswith(r[3].lower())]
    if not mine:
        return ''
    cards = ''.join(f'''<figure class="pj-q" data-reveal><blockquote>“{inline(q)}”</blockquote>
  <figcaption><b>{esc(n)}</b><span>{esc(r)}</span></figcaption></figure>''' for q, n, r, _ in mine)
    return f'<section class="sec pj-quotes" aria-label="What the client says"><div class="pj-q-grid">{cards}</div></section>'


def page_project(slug, order, P):
    p = P[slug]; m, s = p['meta'], p['sec']
    label = m['title']
    heading = m.get('heading', m['title'])
    # the SERVICE(S) line of the credits goes to the left, under the role (both matter most); the rest stays in Credits
    clines = [l.strip() for l in s.get('credits', '').splitlines() if l.strip()]
    svc_line = next((l for l in clines if re.match(r'^\*\*SERVICES?\*\*', l)), '')
    services = re.sub(r'^\*\*SERVICES?\*\*\s*[—-]\s*', '', svc_line)
    services = re.sub(r'(?<=\w)-(?=\w)', '\u2011', services)   # "Full-Service" never breaks at its hyphen
    # under the services: only the client and the agency (when there is one), shown the same way — the team is not shown
    def fact(key):
        l = next((l for l in clines if re.match(rf'^\*\*{key}\*\*', l)), '')
        return re.sub(rf'^\*\*{key}\*\*\s*[—-]\s*', '', l)
    facts = [(lab, v) for lab, v in (('Services', services), ('Client', fact('CLIENT')), ('Agency', fact('AGENCY'))) if v]
    facts_html = ''.join(f'<p class="pj-fact"><strong class="pj-svc-l">{lab}</strong>{inline(v)}</p>' for lab, v in facts)
    lst = [x for x in order]
    nxt = P[lst[(lst.index(slug) + 1) % len(lst)]] if slug in lst else P[lst[0]]
    body = f'''
<article class="project">
  <header class="page-hd pj-hd">
    <h1 class="page-t pj-t" data-split>{esc(heading)}</h1>
  </header>
  <hr class="hd-line">
  <section class="sec lg-row pj-row">
    <div class="pj-left">
      <p class="pj-role" data-reveal>{esc(m["role"])}</p>
      {f'<div class="pj-services" data-reveal>{facts_html}</div>' if facts else ''}
    </div>
    <div class="lg-body pj-intro">{md(s.get("intro", ""), reveal=False)}
    </div>
  </section>
  <div class="pj-media">
{media_rows(s.get("media", ""), slug, label, first_eager=True)}
  </div>
{pj_quotes(m["title"])}
{pj_related(m.get("related", ""), P)}
</article>
<nav class="next" aria-label="Next project">
  <a href="/{nxt["slug"]}">
    <span class="label">Next project</span>
    <span class="next-t">{esc(nxt["meta"]["title"])}</span>
    <span class="next-r">{esc(nxt["meta"]["role"])}</span>
  </a>
</nav>'''
    return layout('/' + slug, m.get('page_title', 'Ranko — ' + m['title']), m.get('description', ''), body, '/work', video=True)


def page_simple(name, path):
    """services / about / afterhours: content/<name>.txt"""
    meta, sec = read_content(os.path.join(CONTENT, name + '.txt'))
    parts = [f'''<section class="page-hd k-hero">
  <h1 class="page-t" data-split>{"<br>".join(inline(x.strip()) for x in meta.get("heading", "").split("|"))}</h1>
  <div class="page-intro" data-split>{md(sec.get("intro", ""), reveal=False).replace(" | ", " <br>")}</div>
</section>''']
    if name != 'services':   # a thin grey line between the header and the page (Services has it on its first row)
        parts.append('<hr class="hd-line">')
    if name == 'services':
        i = 0
        for key in ('films', 'systems', 'ai'):
            if key not in sec: continue
            i += 1
            parts.append(svc_row(sec[key]))
            if key == 'ai' and sec.get('media'):   # the two videos come after the AI text
                parts.append(f'<section class="sec">{media_rows(sec["media"], "services", "Services")}</section>')
        if sec.get('process'):   # under the AI videos: the process, like the reference (text left, the steps in cards on the right)
            parts.append(process(sec['process']))
    elif name == 'about':
        brands = [b.strip() for b in sec.get('brands', '').splitlines() if b.strip() and not b.lstrip().startswith('#')]
        parts.append(f'''{f'<section class="sec statement-2 about-st"><p class="mid-t" data-split>{inline(sec["statement"])}</p></section>' if sec.get("statement") else ""}
<section class="sec brands" aria-labelledby="br-t">
  <h2 id="br-t" class="sec-t" data-reveal>Brands we've worked for</h2>
  <ul class="brand-grid">{"".join(brand_cell(b) for b in brands)}</ul>
</section>
<section class="sec bio">
  <div class="bio-img" data-reveal>{picture("about", "portrait", 1200, 992, meta.get("portrait_alt", ""), "half", label="Portrait")}</div>
  <div class="bio-txt">{md(sec.get("bio", ""))}</div>
</section>
{visit(sec.get("visit", ""))}''')
    elif name == 'afterhours':
        parts.append(mosaic(sec.get('media', ''), name))
    elif name == 'privacy':
        parts.append(legal(sec.get("body", "")))
    else:
        parts.append(f'<section class="sec">{media_rows(sec.get("media", ""), name, name.title(), first_eager=True)}</section>')
    return layout(path, meta['page_title'], meta['description'], '\n'.join(parts), path, video=name not in ('about', 'privacy'))


LOGOS = os.path.join(SRC, 'assets/logos')


def logo_ratio(path):
    """width / height of a logo file (SVG viewBox, WebP or PNG header)."""
    if path.endswith('.svg'):
        head = open(path, encoding='utf-8', errors='ignore').read(3000)
        m = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', head)
        if not m: m = re.search(r'<svg[^>]*?\bwidth="([\d.]+)[^"]*"[^>]*?\bheight="([\d.]+)', head)
        return float(m.group(1)) / float(m.group(2)) if m else 2
    if path.endswith('.webp'):
        w, h = webp_size(path)
        return w / h
    with open(path, 'rb') as f:
        b = f.read(24)
    return int.from_bytes(b[16:20], 'big') / int.from_bytes(b[20:24], 'big')


def brand_cell(line):
    """About: one cell of the logo wall. The logo file is src/assets/logos/<slug>.svg (already black),
    <slug>.k.png (shown as a black silhouette), <slug>.g.png (shown in greys) or <slug>.c.png (colours pushed to black and white); no file: the name in text.
    Sizes follow the logo's shape so wide and square logos look the same weight."""
    name, _, link = (x.strip() for x in line.partition(' = '))   # "Dior = dior": the logo opens the project page
    slug = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()).strip('-')
    files = [f for f in os.listdir(LOGOS) if f.split('.')[0] == slug] if os.path.isdir(LOGOS) else []
    wrap = (lambda x: f'<a class="brand-link" href="/{link}" aria-label="{esc(name)}: see the project">{x}</a>') if link else (lambda x: x)
    if not files:
        txt = '<span class="brand-txt">' + esc(name) + '</span>'
        return f'<li class="brand" data-reveal>{wrap(txt)}</li>'
    f = files[0]
    r = logo_ratio(os.path.join(LOGOS, f))
    w = min(132, 54 * r ** .5); h = min(52, w / r); w = h * r
    tone = {'k': ' is-k', 'g': ' is-g', 'c': ' is-c'}.get(f.split('.')[1] if f.count('.') == 2 else '', '')
    img = (f'<img class="brand-logo{tone} logo-{slug}" src="/assets/logos/{f}?v={ver("assets/logos/" + f)}" '
           f'alt="{esc(name)}" width="{w:.0f}" height="{h:.0f}" loading="lazy" decoding="async">')
    return f'<li class="brand" data-reveal>{wrap(img)}</li>'


def visit(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines: return ''
    q = '+'.join(' '.join(lines[1:]).replace(',', '').split())
    maps = f'https://www.google.com/maps/search/?api=1&query={q}'
    addr = '<br>'.join(re.sub(r'([A-Z]\d[A-Z]) (\d[A-Z]\d)', '\\1\u00a0\\2', esc(l)) for l in lines[1:])   # postal code kept on one line
    # like the tiles of the bottom of the page, mirrored: the address in a narrow tile on the left (like "AI talent wanted"),
    # the e-mail in the long black tile on the right (like "Work with us"); colours swap on hover
    return f'''<section class="sec visit" aria-label="Contact">
  <div class="visit-grid">
    <a class="visit-addr" href="{maps}" target="_blank" rel="noopener" data-reveal><span class="visit-go">Open in Google Maps ↗</span><address>{addr}</address></a>
    <a class="visit-mail" href="{MAIL}" data-reveal><span>Work with us</span><span>hello@ranko.ca</span></a>
  </div>
</section>'''


def page_404():
    body = '''<section class="page-hd"><h1 class="page-t">Page not found</h1>
<p class="page-intro"><a class="link-big" href="/">Back to home</a></p></section>'''
    return layout('/404', 'Ranko — Page not found', '', body)


# ---------------------------------------------------------------- IMAGES.md

def write_images_md():
    lines = ['# Images du site Ranko', '',
             'Ce fichier est mis à jour automatiquement à chaque fabrication du site (`python3 build.py`).', '',
             '**Comment remplacer une image de remplacement :**', '',
             '1. Exportez votre visuel en **WebP** aux dimensions indiquées (le rapport largeur/hauteur compte ; la taille exacte peut varier un peu).',
             '2. Nommez-le exactement comme dans la colonne « Fichier ».',
             '3. Déposez-le dans le dossier indiqué (créez le dossier s’il n’existe pas).',
             '4. Relancez `python3 build.py` : l’image remplace automatiquement l’encart.', '',
             'Astuce : le site gratuit https://squoosh.app convertit une image en WebP (réglage « Quality » ~75).', '',
             '✅ = votre image est en place · ⬜ = image de remplacement affichée', '']
    groups = {}
    for owner, slot, w, h, real in SLOTS:
        groups.setdefault(owner, {})[slot] = (w, h, real)
    video_note = False
    for owner in groups:
        lines += [f'## {owner}', '', '| | Fichier | Dimensions | Format | Dossier |', '|---|---|---|---|---|']
        for slot, (w, h, real) in groups[owner].items():
            if slot.startswith('video-'): continue
            fname, fmt = (slot, 'MP4 (vidéo muette en boucle)') if slot.endswith('.mp4') else (slot + '.webp', 'WebP')
            lines.append(f'| {"✅" if real else "⬜"} | `{fname}` | {w} × {h} | {fmt} | `images/{owner}/` |')
        vids = [(s, v) for s, v in groups[owner].items() if s.startswith('video-')]
        if vids:
            video_note = True
            lines += ['', f'<details><summary>Images d’attente des vidéos ({len(vids)}, facultatif)</summary>', '',
                      '| | Fichier | Dimensions | Dossier |', '|---|---|---|---|']
            lines += [f'| {"✅" if r else "⬜"} | `{s}.webp` | {w} × {h} | `images/{owner}/` |' for s, (w, h, r) in vids]
            lines += ['', '</details>']
        lines.append('')
    if video_note:
        lines += ['---', '',
                  '**Images d’attente des vidéos (facultatif)** : chaque vidéo Vimeo affiche une image le temps de se charger. '
                  'Vous pouvez y mettre une image tirée de la vidéo, sinon l’image de remplacement est utilisée.', '']
    open(os.path.join(ROOT, 'IMAGES.md'), 'w', encoding='utf-8').write('\n'.join(lines))


# ---------------------------------------------------------------- build

def italic_ranko(page):
    """The word "Ranko" is set in italics in the descriptive texts only:
    not in links, addresses, header, footer, buttons, quotes, attributes, <head> or scripts (a link can still ask for it with <em>)."""
    head, sep, body = page.partition('<body>')
    if not sep:
        return page
    out, skip, em = [], 0, 0
    for part in re.split(r'(<[^>]+>)', body):
        if part.startswith('<'):
            tag = re.match(r'</?\s*([a-zA-Z0-9]+)', part)
            name = tag.group(1).lower() if tag else ''
            closing = part.startswith('</')
            if name in ('script', 'style', 'svg', 'title', 'a', 'header', 'footer', 'nav', 'button', 'address', 'blockquote'):   # blockquote: the clients' own words
                skip += -1 if closing else (0 if part.endswith('/>') else 1)
            elif name == 'em':
                em += -1 if closing else 1
            out.append(part)
        elif skip or em:
            out.append(part)
        else:
            out.append(re.sub(r'(?<![\w.@/-])Ranko(?![\w.@-])', '<em>Ranko</em>', part))
    return head + sep + ''.join(out)


def write(path, content):
    if path.endswith('.html'):
        content = italic_ranko(content)
    full = os.path.join(DIST, path.lstrip('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(content)


def build():
    global CSS
    CSS = css()
    if os.path.exists(DIST): shutil.rmtree(DIST)
    shutil.copytree(os.path.join(SRC, 'assets'), os.path.join(DIST, 'assets'),
                    ignore=shutil.ignore_patterns('css', 'placeholder-source.webp', '*.jpg', '.DS_Store'))
    if os.path.isdir(IMAGES):
        shutil.copytree(IMAGES, os.path.join(DIST, 'images'), ignore=shutil.ignore_patterns('.DS_Store', '*.md'))
    for f in os.listdir(os.path.join(SRC, 'static')):
        shutil.copy(os.path.join(SRC, 'static', f), os.path.join(DIST, f))
    order, P = load_projects()
    # /dior is served from dior.html (same addresses as the Squarespace site, no redirect)
    pages = {'/index.html': page_home(order, P), '/work.html': page_work(order, P)}
    for name in ('services', 'about', 'afterhours', 'privacy'):
        pages[f'/{name}.html'] = page_simple(name, '/' + name)
    for slug in P:
        pages[f'/{slug}.html'] = page_project(slug, order, P)
    pages['/404.html'] = page_404()
    for path, content in pages.items(): write(path, content)
    urls = ['/'] + [p[:-5] for p in pages if p not in ('/index.html', '/404.html')]
    write('/sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + ''.join(f'  <url><loc>{SITE_URL}{u}</loc></url>\n' for u in urls) + '</urlset>\n')
    write_images_md()
    if _vimeo_dirty:
        json.dump(VIMEO, open(_vimeo_sizes_path, 'w'), indent=0)
    missing = sum(1 for s in SLOTS if not s[4] and not s[1].startswith('video-'))
    print(f'Site built in dist/ — {len(pages)} pages, {missing} image(s) still using the placeholder (see IMAGES.md).')


def serve(port=8080):
    import http.server, functools

    class Handler(http.server.SimpleHTTPRequestHandler):
        # like the hosting: /dior serves dior.html, unknown pages get 404.html
        def send_head(self):
            path = self.path.split('?')[0].split('#')[0]
            if path != '/' and not os.path.splitext(path)[1] and os.path.exists(os.path.join(DIST, path.strip('/') + '.html')):
                self.path = path.rstrip('/') + '.html'
            elif not os.path.exists(os.path.join(DIST, path.lstrip('/'))):
                self.path = '/404.html'
            return super().send_head()

        # preview only: never let the browser keep an old version of a page
        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            super().end_headers()
    handler = functools.partial(Handler, directory=DIST)
    print(f'Preview: http://localhost:{port}  (Ctrl+C to stop)')
    http.server.ThreadingHTTPServer(('127.0.0.1', port), handler).serve_forever()


def check_site():
    """Safety check before publishing: every image, video, page and file used by the site must exist.
    Returns the list of problems (empty = all good)."""
    problems = []
    # 1. image slots that fell back to the purple placeholder (a missing or misnamed image file)
    for owner, slot, w, h, real in SLOTS:
        if not real:
            problems.append(f'Image manquante : images/{owner}/{slot}' + ('' if slot.endswith('.mp4') else '.webp'))
    # 2. every local file or page referenced by the built pages
    refs = re.compile(r'(?:src|href|poster|data-src)="(/[^"#?]*)|srcset="([^"]+)"')
    for page in sorted(f for f in os.listdir(DIST) if f.endswith('.html')):
        html_ = open(os.path.join(DIST, page), encoding='utf-8').read()
        for m in refs.finditer(html_):
            paths = [m.group(1)] if m.group(1) else [p.split()[0] for p in m.group(2).split(',') if p.strip().startswith('/')]
            for p in paths:
                p = p.split('?')[0]
                if p.startswith('//') or p in ('/', ''): continue
                f = os.path.join(DIST, p.lstrip('/'))
                if not (os.path.exists(f) or os.path.exists(f.rstrip('/') + '.html')):
                    problems.append(f'Lien cassé dans {page} : {p}')
    return sorted(set(problems))


if __name__ == '__main__':
    build()
    problems = check_site()
    if problems:
        print(f'\n⚠️  VÉRIFICATION : {len(problems)} problème(s) — à corriger avant de publier :')
        for p in problems[:40]: print('   - ' + p)
        if len(problems) > 40: print(f'   … et {len(problems) - 40} autre(s)')
    else:
        print('✅ Vérification : toutes les images, vidéos, pages et liens du site sont présents.')
    # "python3 build.py check" (used by the hosting): refuse to publish if anything is missing,
    # so the version already online stays in place.
    if len(sys.argv) > 1 and sys.argv[1] == 'check' and problems:
        sys.exit(1)
    if len(sys.argv) > 1 and sys.argv[1] == 'serve':
        serve(int(sys.argv[2]) if len(sys.argv) > 2 else 8080)   # python3 build.py serve 8090
