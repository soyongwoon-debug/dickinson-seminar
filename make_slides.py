#!/usr/bin/env python3
"""
Generate a landscape PDF slide deck for the Deppman/Dickinson seminar presentation.
Pure standard library (no external deps) — writes a valid PDF with the built-in
Helvetica font family. Handles word-wrapping and simple bullet/heading styling.
"""

import zlib

# ---------------------------------------------------------------------------
# Minimal PDF writer
# ---------------------------------------------------------------------------

PAGE_W, PAGE_H = 792, 612  # US Letter landscape (points)

# Built-in font widths approximation: use Helvetica AFM-ish average.
# For layout we use per-character widths from a compact table (units/1000).
HELV_WIDTHS = {
    ' ': 278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667,
    "'": 191, '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333,
    '.': 278, '/': 278, '0': 556, '1': 556, '2': 556, '3': 556, '4': 556,
    '5': 556, '6': 556, '7': 556, '8': 556, '9': 556, ':': 278, ';': 278,
    '<': 584, '=': 584, '>': 584, '?': 556, '@': 1015, 'A': 667, 'B': 667,
    'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278,
    'J': 500, 'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778, 'P': 667,
    'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944,
    'X': 667, 'Y': 667, 'Z': 611, '[': 278, '\\': 278, ']': 278, '^': 469,
    '_': 556, '`': 333, 'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556,
    'f': 278, 'g': 556, 'h': 556, 'i': 222, 'j': 222, 'k': 500, 'l': 222,
    'm': 833, 'n': 556, 'o': 556, 'p': 556, 'q': 556, 'r': 333, 's': 500,
    't': 278, 'u': 556, 'v': 500, 'w': 722, 'x': 500, 'y': 500, 'z': 500,
    '{': 334, '|': 260, '}': 334, '~': 584,
}
HELV_BOLD_WIDTHS = dict(HELV_WIDTHS)
HELV_BOLD_WIDTHS.update({
    'a': 556, 'c': 556, 'e': 556, 'f': 333, 'r': 389, 's': 556, 't': 333,
    ' ': 278, 'i': 278, 'j': 278, 'l': 278, 'A': 722, 'B': 722, 'F': 611,
})


def char_width(ch, size, bold=False):
    table = HELV_BOLD_WIDTHS if bold else HELV_WIDTHS
    return table.get(ch, 556) / 1000.0 * size


def text_width(s, size, bold=False):
    return sum(char_width(c, size, bold) for c in s)


def wrap(text, size, max_w, bold=False):
    """Greedy word-wrap. Returns list of lines."""
    words = text.split(' ')
    lines, cur = [], ''
    for w in words:
        trial = w if not cur else cur + ' ' + w
        if text_width(trial, size, bold) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def esc(s):
    return s.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')


def sanitize(s):
    """Map common unicode punctuation to Latin-1 safe equivalents."""
    repl = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '--', '\u2026': '...', '\u2022': '-',
        '\u2192': '->', '\u2b50': '*', '\u26a0': '!', '\u00e0': 'a',
        '\u00e9': 'e', '\u00ef': 'i', '\u2011': '-',
    }
    return ''.join(repl.get(c, c if ord(c) < 256 else '?') for c in s)


class PDF:
    def __init__(self):
        self.objs = []  # list of raw byte strings (object bodies)
        self.pages = []

    def add_obj(self, body):
        self.objs.append(body)
        return len(self.objs)  # 1-based object number

    def add_page(self, content_stream):
        data = content_stream.encode('latin-1', 'replace')
        compressed = zlib.compress(data)
        stream_obj = (
            b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(compressed)
            + compressed + b'\nendstream'
        )
        content_num = self.add_obj(stream_obj)
        self.pages.append(content_num)

    def build(self, path):
        # Font objects
        f_reg = self.add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
        f_bold = self.add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
        f_obl = self.add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>')

        # Page objects reference a shared Pages node (added later) — we need its num.
        pages_node_num = len(self.objs) + len(self.pages) + 1  # placeholder calc
        # Simpler: create page objects now, patch parent afterwards.
        page_obj_nums = []
        resources = (
            b'<< /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >>' % (f_reg, f_bold, f_obl)
        )
        for content_num in self.pages:
            body = (
                b'<< /Type /Page /Parent __PARENT__ 0 R '
                b'/MediaBox [0 0 %d %d] /Resources %s /Contents %d 0 R >>'
                % (PAGE_W, PAGE_H, resources, content_num)
            )
            page_obj_nums.append(self.add_obj(body))

        kids = b' '.join(b'%d 0 R' % n for n in page_obj_nums)
        pages_num = self.add_obj(
            b'<< /Type /Pages /Kids [%s] /Count %d >>' % (kids, len(page_obj_nums))
        )
        # Patch parent refs
        for n in page_obj_nums:
            self.objs[n - 1] = self.objs[n - 1].replace(b'__PARENT__', b'%d' % pages_num)

        catalog_num = self.add_obj(b'<< /Type /Catalog /Pages %d 0 R >>' % pages_num)

        # Serialize
        out = [b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n']
        offsets = []
        pos = len(out[0])
        for i, body in enumerate(self.objs, start=1):
            obj = b'%d 0 obj\n' % i + body + b'\nendobj\n'
            offsets.append(pos)
            out.append(obj)
            pos += len(obj)
        xref_pos = pos
        n = len(self.objs)
        xref = [b'xref\n', b'0 %d\n' % (n + 1), b'0000000000 65535 f \n']
        for off in offsets:
            xref.append(b'%010d 00000 n \n' % off)
        out.extend(xref)
        out.append(
            b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n'
            % (n + 1, catalog_num, xref_pos)
        )
        with open(path, 'wb') as fh:
            fh.write(b''.join(out))


# ---------------------------------------------------------------------------
# Slide rendering
# ---------------------------------------------------------------------------

MARGIN = 54
ACCENT = (0.13, 0.30, 0.52)     # deep blue
DARK = (0.12, 0.12, 0.14)
GRAY = (0.40, 0.40, 0.44)
QUOTE_BG = (0.93, 0.95, 0.98)


def col(c):
    return '%.3f %.3f %.3f' % c


def render_slide(slide, idx, total):
    """slide = dict(title, subtitle?, blocks[]). Returns content stream string."""
    s = []
    # Background
    s.append('q 1 1 1 rg 0 0 %d %d re f Q' % (PAGE_W, PAGE_H))
    # Top accent bar
    s.append('q %s rg 0 %d %d 8 re f Q' % (col(ACCENT), PAGE_H - 8, PAGE_W))
    # Footer
    footer = sanitize('Deppman, "Trying to Think with Emily Dickinson" (2005)')
    s.append('q BT /F1 9 Tf %s rg %d 24 Td (%s) Tj ET Q' % (col(GRAY), MARGIN, esc(footer)))
    pagenum = '%d / %d' % (idx, total)
    pw = text_width(pagenum, 9)
    s.append('q BT /F1 9 Tf %s rg %.1f 24 Td (%s) Tj ET Q' % (col(GRAY), PAGE_W - MARGIN - pw, esc(pagenum)))

    y = PAGE_H - 62
    max_w = PAGE_W - 2 * MARGIN

    # Title
    title = sanitize(slide['title'])
    for ln in wrap(title, 26, max_w, bold=True):
        s.append('q BT /F2 26 Tf %s rg %d %.1f Td (%s) Tj ET Q' % (col(ACCENT), MARGIN, y, esc(ln)))
        y -= 32
    y -= 6
    # underline
    s.append('q %s RG 1.2 w %d %.1f m %d %.1f l S Q' % (col(ACCENT), MARGIN, y, PAGE_W - MARGIN, y))
    y -= 24

    for block in slide['blocks']:
        btype = block[0]
        if btype == 'text':
            _, txt, opts = block
            size = opts.get('size', 14)
            bold = opts.get('bold', False)
            italic = opts.get('italic', False)
            color = opts.get('color', DARK)
            font = '/F2' if bold else ('/F3' if italic else '/F1')
            for ln in wrap(sanitize(txt), size, max_w, bold=bold):
                s.append('q BT %s %d Tf %s rg %d %.1f Td (%s) Tj ET Q'
                         % (font, size, col(color), MARGIN, y, esc(ln)))
                y -= size + 6
            y -= opts.get('gap', 4)
        elif btype == 'bullet':
            _, txt, opts = block
            size = opts.get('size', 14)
            indent = opts.get('indent', 0)
            color = opts.get('color', DARK)
            bx = MARGIN + 6 + indent
            marker = '-' if indent > 0 else 'n'  # 'n' -> we draw a box via char
            lines = wrap(sanitize(txt), size, max_w - 22 - indent, bold=False)
            # bullet marker
            if indent == 0:
                s.append('q %s rg %d %.1f 5 5 re f Q' % (col(ACCENT), MARGIN + indent, y + 2))
            else:
                s.append('q BT /F1 %d Tf %s rg %d %.1f Td (-) Tj ET Q'
                         % (size, col(GRAY), MARGIN + indent, y))
            for j, ln in enumerate(lines):
                s.append('q BT /F1 %d Tf %s rg %d %.1f Td (%s) Tj ET Q'
                         % (size, col(color), bx + 12, y, esc(ln)))
                y -= size + 5
            y -= 3
        elif btype == 'quote':
            _, txt, opts = block
            size = opts.get('size', 13)
            lines = wrap(sanitize(txt), size, max_w - 40)
            box_h = len(lines) * (size + 6) + 14
            # background
            s.append('q %s rg %d %.1f %d %.1f re f Q'
                     % (col(QUOTE_BG), MARGIN, y - box_h + size + 2, max_w, box_h))
            # left rule
            s.append('q %s rg %d %.1f 4 %.1f re f Q'
                     % (col(ACCENT), MARGIN, y - box_h + size + 2, box_h))
            ty = y - 6
            for ln in lines:
                s.append('q BT /F3 %d Tf %s rg %d %.1f Td (%s) Tj ET Q'
                         % (size, col(DARK), MARGIN + 16, ty, esc(ln)))
                ty -= size + 6
            y -= box_h + 10
        elif btype == 'space':
            y -= block[1]
    return ''.join(s)


def render_title_slide(slide, idx, total):
    s = []
    s.append('q %s rg 0 0 %d %d re f Q' % (col(ACCENT), PAGE_W, PAGE_H))
    # big title
    y = PAGE_H - 250
    for ln in wrap(sanitize(slide['title']), 40, PAGE_W - 140, bold=True):
        w = text_width(ln, 40, bold=True)
        s.append('q BT /F2 40 Tf 1 1 1 rg %.1f %.1f Td (%s) Tj ET Q'
                 % ((PAGE_W - w) / 2, y, esc(ln)))
        y -= 50
    y -= 20
    for line in slide['blocks']:
        txt = sanitize(line)
        w = text_width(txt, 16)
        s.append('q BT /F1 16 Tf 0.85 0.90 0.97 rg %.1f %.1f Td (%s) Tj ET Q'
                 % ((PAGE_W - w) / 2, y, esc(txt)))
        y -= 28
    return ''.join(s)


# ---------------------------------------------------------------------------
# Slide content
# ---------------------------------------------------------------------------

def B(txt, **o):      return ('bullet', txt, o)
def T(txt, **o):      return ('text', txt, o)
def Q(txt, **o):      return ('quote', txt, o)
def SP(h):            return ('space', h)


slides = []

# 1 — Title
slides.append({'kind': 'title',
    'title': 'Trying to Think with Emily Dickinson',
    'blocks': [
        'Jed Deppman (2005)  -  The Emily Dickinson Journal 14.1: 84-103',
        '',
        'Presented by [Your Name]',
        '[Course / Date]',
    ]})

# 2
slides.append({'title': 'Two Epigraphs: The Central Tension', 'blocks': [
    Q('"Why not an \'eleventh hour\' in the life of the mind as well as such an one in the life of the soul..."  -- Dickinson to Austin, 1851 (L44)'),
    Q('"the more consciousness, the more intense the despair."  -- Kierkegaard, Sickness unto Death'),
    B('Dickinson: thinking is an existential drama, equal to the soul\'s.'),
    B('Kierkegaard: deeper consciousness = deeper despair.'),
    B('The paper lives in the gap between these two claims.', bold=True),
]})

# 3
slides.append({'title': 'The Critical Debate', 'blocks': [
    T('The received view (what Deppman opposes):', bold=True, size=15),
    B('Dickinson privileges emotional / physical response over clarity of thought.'),
    B('Peterson: her impassioned poems become "a series of ecstatic assertions, an abandonment to excess verging on mental unbalance" (500).'),
    SP(6),
    T('Deppman\'s entry point:', bold=True, size=15),
    B('Her "famous opacity" has led readers to treat affect as primary.'),
    B('He will "argue the opposite case."'),
]})

# 4
slides.append({'title': 'The Thesis', 'blocks': [
    Q('"...I will argue the opposite case and portray her not as a mystic but as a serious thinker." (p. 85)'),
    B('Not "ecstatic assertions" -> but "careful sequences of ideas and images."'),
    B('Not "abandonment to excess" -> but "thoughtful production of, and reaction to, extreme states of being."'),
    SP(4),
    T('Goal: how Dickinson conceived the activity of thinking, and "how writing poetry helped her think." (p. 85)', bold=True, size=14),
]})

# 5
slides.append({'title': 'Evidence 1: Word Statistics', 'blocks': [
    T('Rosenbaum Concordance (1955 Johnson edition):', size=14),
    B('Feeling-words:  feel 39  /  felt 35  /  feels 16  /  feeling 8  /  body 10  /  bodies 1'),
    B('Thinking-words:  thought 69  /  think 43  /  know 230  /  knew 80  /  mind 79  /  brain 26'),
    SP(6),
    B('"know" = 4th most common verb overall (after be, be able, have).'),
    B('Deppman: "much more about thought than feeling" (p. 86).'),
    B('BUT his own caveat: statistics are "partial and decontextualized" (p. 86).', bold=True),
]})

# 6
slides.append({'title': 'Evidence 2: The Many Faces of Thought', 'blocks': [
    T('Thought is a "consistent as well as kaleidoscopic" topic (p. 85):', size=14),
    B('Celebratory: "Best Things dwell out of Sight / ... Our Thought" (Fr1012)'),
    B('Cautionary: "If wrecked upon the Shoal of Thought..." (Fr1503)'),
    B('Analytic: "The Brain - is wider than the Sky -" (Fr598)'),
    B('Wild / dangerous: "The Brain, within it\'s Groove / Runs evenly ... But let a Splinter swerve -" (Fr563)'),
    B('Sufficient for happiness: "The revery alone will do, / If bees are few" (Fr1779)'),
]})

# 7
slides.append({'title': 'Framework 1: Postmodern Dickinson', 'blocks': [
    B('Wolff: "artist of the age of transition" - freeing language "from the tyranny of His definitions" (429).'),
    B('Porter: the mind "explosive with signifying power but disinherited from transcendent knowledge" (7).'),
    B('Lyotard: postmodernism = "incredulity toward metanarratives."'),
    B('Derrida: Dickinson as "bricoleuse," mixing religious / literary / scientific vocabularies.'),
    SP(4),
    T('Root condition: tension between Lockean empiricism (schoolbooks) and Kantian / Transcendentalist apprehension of the supersensible (p. 86).', bold=True, size=13),
]})

# 8
slides.append({'title': 'Framework 2: The Kantian Sublime', 'blocks': [
    T('The engine of the whole paper:', bold=True, size=15),
    B('1. Reason conceives something conceivable but unpresentable (infinity, death).'),
    B('2. Reason demands an adequate image.'),
    B('3. Imagination tries -- and fails.'),
    B('4. The mind repeats the try; from this the sublime emerges.'),
    Q('Lyotard: "it is our business not to supply reality but to invent allusions to the conceivable which cannot be presented" (Postmodern 81).'),
    T('! Key concession: Dickinson "did not read Kant" (p. 87) - a shared attitude, not influence.', bold=True, size=13, color=(0.6,0.1,0.1)),
]})

# 9
slides.append({'title': 'The Origin of "Trying" (L10, 1846)', 'blocks': [
    T('At age 15, Dickinson tries to think her own death:', size=14),
    Q('"I cannot imagine with the farthest stretch of my imagination my own death scene... I cannot realize that the grave will be my last home..."'),
    B('The refrain: "I cannot imagine ... I cannot realize ... nor can I realize ..."'),
    B('The mind "stretches, fails, realizes it fails, regroups, rewords, and reaches its limit again" (p. 88).'),
    B('Core formula: "she cannot think death or Eternity ... but she cannot not think them either."', bold=True),
]})

# 10
slides.append({'title': 'Evidence 3: The Higginson Letters', 'blocks': [
    T('Writing understood AS thought:', bold=True, size=14),
    B('1862 (L260): "Are you too deeply occupied to say if my Verse is alive?"'),
    B('The bind (L260): "The Mind is so near itself - it cannot see, distinctly - and I have none to ask -."'),
    B('Writing as therapy (L261): "I had a terror ... and so I sing, as the Boy does by the Burying Ground - because I am afraid."'),
    B('Thought over language (L261): "While my thought is undressed - I can make the distinction, but when I put them in the Gown - they look alike, and numb."'),
    B('To the end (L1042): "bereft of Book and Thought, by the doctor\'s reproof."'),
]})

# 11
slides.append({'title': 'Defining the "Try-to-Think" Poem', 'blocks': [
    B('Purpose: to force the mind to satisfy reason\'s unsatisfiable demand for a complete image.'),
    B('"the try is usually serious, the goal explicitly stated, ... emphasis squarely on the willful movements of thought."'),
    B('They are "precisely sequenced, if difficult, thought experiments" - readers repeat the steps.'),
    SP(6),
    T('Examples: "Of Death I try to think like this" (Fr1588); "The nearest Dream recedes" (Fr304B); "I think To Live - may be a Bliss" (Fr757).', bold=True, size=13),
]})

# 12
slides.append({'title': 'Close Reading 1: Fr570 & the Dilemma', 'blocks': [
    Q('I tried to think a lonelier Thing / Than any I had seen - / Some Polar Expiation - An Omen in the Bone / Of Death\'s tremendous nearness - ... I plucked at our Partition - ... I almost strove to clasp his Hand, / Such Luxury - it grew - / That as Myself - could pity Him - / Perhaps he - pitied me -', size=12),
    T('The interpretive dilemma (p. 94):', bold=True, size=14),
    B('Proactive? - a "virtuoso attempt to conceptualize an extreme human possibility"'),
    B('Reactive? - an attempt "to knead it, battle it, alter it, realize it, or just survive it through thought"'),
    B('Deppman chooses: REACTIVE.', bold=True),
]})

# 13
slides.append({'title': 'Close Reading 2: Tracking the Steps', 'blocks': [
    B('1. Naming the "Thing" -> two quiddities:'),
    B('"Some Polar Expiation" - expiation + polar expedition: radical exile from self, culture, nature.', indent=18),
    B('"An Omen in the Bone / Of Death\'s tremendous nearness" - anticipatory; near in time AND space.', indent=18),
    B('2. Borrowing a "Duplicate" - a fellow spirit "Of Heavenly Love - forgot -": the "smallest possible unit of imagined community."'),
    B('3. "Within the Clutch of Thought" - undecidability: reachable BY thought, or made ONLY of thought (= fabricated)?'),
    B('4. "our Partition" - the possessive forms "a we": bridge AND barrier between living self and dead twin.'),
]})

# 14
slides.append({'title': 'Close Reading 3: The Paradoxical Close', 'blocks': [
    Q('I almost strove to clasp his Hand, / Such Luxury - it grew - / That as Myself - could pity Him - / Perhaps he - pitied me -'),
    B('Two God-forsaken souls in "Opposing Cells" - "a chilling scene reminiscent of Beckett\'s Godot."'),
    B('Deppman hears an elided phrase: "Such Luxury - it grew [- to think]."'),
    B('-> Consolation comes from the experimental force of thought itself.'),
    B('BUT: "a fragile state and a momentary victory" - how long can it console?', bold=True),
]})

# 15
slides.append({'title': 'Critical Assessment: Strengths', 'blocks': [
    B('Methodological rigor - grounds a large claim in concordance data (p. 86), not impression. A falsifiable move.'),
    B('Genuine integration - letters (L10, L260, L261) function as evidence of a poetics, not decorative biography.'),
    B('A generative concept - the "try-to-think poem" names a real, repeatable pattern, applicable beyond his sample.'),
    B('Reframes opacity as method - difficulty is the trace of a mind at work, not failure or excess.'),
]})

# 16
slides.append({'title': 'Critical Assessment: My Position', 'blocks': [
    T('Claim: the thesis is self-undermining - and that is its most interesting result.', bold=True, size=15, color=(0.6,0.1,0.1)),
    B('Deppman picks thought over feeling. Yet his own reading of Fr570 runs on affect: "desperate," "chilling," "sickening loneliness," writing as "thought\'s psychotherapeutic response to troubling emotion" (p. 90).'),
    B('If the "try" matters only BECAUSE the loneliness is unbearable, then thought and feeling are inseparable - the binary collapses.'),
    B('So the real achievement is the opposite of the stated one: thinking IS an emotional act.', bold=True),
    SP(4),
    T('Discussion bait: "Kant without Kant" (p.87) - imported lens?  /  Circularity of the genre.  /  Muldoon\'s Civil War reading (note 18).', size=12, color=GRAY),
]})

# 17
slides.append({'title': 'Conclusion & Discussion Questions', 'blocks': [
    B('Deppman: these are poems in which she "tried to help or save herself by representing her own efforts to help or save herself" (p. 100).'),
    B('To join the poem is to risk "experiencing a loneliness we cannot sound."'),
    B('Return to Kierkegaard: thought is both consolation AND risk.', bold=True),
    SP(8),
    T('Discussion questions:', bold=True, size=15),
    B('1. Does the thought/feeling binary survive Deppman\'s own close reading?'),
    B('2. Is the Kantian sublime valid for a poet who never read Kant?'),
    B('3. Is "try-to-think" a discovered genre or a critic\'s construct?'),
    B('4. Whose reading of Fr570 convinces you - Deppman\'s or Muldoon\'s?'),
]})


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

pdf = PDF()
total = len(slides)
for i, sl in enumerate(slides, start=1):
    if sl.get('kind') == 'title':
        content = render_title_slide(sl, i, total)
    else:
        content = render_slide(sl, i, total)
    pdf.add_page(content)

pdf.build('/projects/sandbox/dickinson_presentation.pdf')
print('Wrote dickinson_presentation.pdf with %d slides' % total)
