#!/usr/bin/env python3
"""
Generate a plain, minimal landscape PDF slide deck (Times-Roman serif) for the
Deppman/Dickinson seminar presentation. Style modeled on a reference deck:
white background, no decoration, centered bold titles, left-aligned bullets.
Pure standard library (no external deps).
"""

import zlib

PAGE_W, PAGE_H = 792, 612  # US Letter landscape (points)

# --- Times-Roman AFM widths (units/1000) ---
TIMES = {
    ' ':250,'!':333,'"':408,'#':500,'$':500,'%':833,'&':778,"'":180,'(':333,
    ')':333,'*':500,'+':564,',':250,'-':333,'.':250,'/':278,'0':500,'1':500,
    '2':500,'3':500,'4':500,'5':500,'6':500,'7':500,'8':500,'9':500,':':278,
    ';':278,'<':564,'=':564,'>':564,'?':444,'@':921,'A':722,'B':667,'C':667,
    'D':722,'E':611,'F':556,'G':722,'H':722,'I':333,'J':389,'K':722,'L':611,
    'M':889,'N':722,'O':722,'P':556,'Q':722,'R':667,'S':556,'T':611,'U':722,
    'V':722,'W':944,'X':722,'Y':722,'Z':611,'[':333,'\\':278,']':333,'^':469,
    '_':500,'`':333,'a':444,'b':500,'c':444,'d':500,'e':444,'f':333,'g':500,
    'h':500,'i':278,'j':278,'k':500,'l':278,'m':778,'n':500,'o':500,'p':500,
    'q':500,'r':333,'s':389,'t':278,'u':500,'v':500,'w':722,'x':500,'y':500,
    'z':444,'{':480,'|':200,'}':480,'~':541,
}
TIMES_BOLD = {
    ' ':250,'!':333,'"':555,'#':500,'$':500,'%':1000,'&':833,"'":278,'(':333,
    ')':333,'*':500,'+':570,',':250,'-':333,'.':250,'/':278,'0':500,'1':500,
    '2':500,'3':500,'4':500,'5':500,'6':500,'7':500,'8':500,'9':500,':':333,
    ';':333,'<':570,'=':570,'>':570,'?':500,'@':930,'A':722,'B':667,'C':722,
    'D':722,'E':667,'F':611,'G':778,'H':778,'I':389,'J':500,'K':778,'L':667,
    'M':944,'N':722,'O':778,'P':611,'Q':778,'R':722,'S':556,'T':667,'U':722,
    'V':722,'W':1000,'X':722,'Y':722,'Z':667,'[':333,'\\':278,']':333,'^':581,
    '_':500,'`':333,'a':500,'b':556,'c':444,'d':556,'e':444,'f':333,'g':500,
    'h':556,'i':278,'j':333,'k':556,'l':278,'m':833,'n':556,'o':500,'p':556,
    'q':556,'r':444,'s':389,'t':333,'u':556,'v':500,'w':722,'x':500,'y':500,
    'z':444,'{':394,'|':220,'}':394,'~':520,
}


_CURLY_W = {  # widths for curly punctuation (units/1000), Times regular & bold
    '\u2018': (333, 333), '\u2019': (333, 333),
    '\u201c': (444, 500), '\u201d': (444, 500),
    '\u2013': (500, 500), '\u2014': (1000, 1000), '\u2026': (1000, 1000),
}


def char_width(ch, size, bold=False):
    if ch in _CURLY_W:
        return _CURLY_W[ch][1 if bold else 0] / 1000.0 * size
    table = TIMES_BOLD if bold else TIMES
    return table.get(ch, 500) / 1000.0 * size


def text_width(s, size, bold=False):
    return sum(char_width(c, size, bold) for c in s)


def wrap(text, size, max_w, bold=False):
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
    # 1) escape PDF-special chars first (must be before adding our own backslashes)
    s = s.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')
    # 2) map unicode curly punctuation to WinAnsi octal escapes
    for u, code in WINANSI.items():
        s = s.replace(u, code)
    # 3) drop / downgrade any remaining non-latin
    drop = {'\u2022': '-', '\u2192': '->', '\u2b50': '', '\u26a0': '',
            '\u00e0': 'a', '\u00e9': 'e', '\u00ef': 'i', '\u2011': '-'}
    for u, r in drop.items():
        s = s.replace(u, r)
    return s


# WinAnsi (CP1252) byte codes for curly punctuation, emitted as \ooo octal escapes.
WINANSI = {
    '\u2018': '\\221',  # left single quote  '
    '\u2019': '\\222',  # right single quote '
    '\u201c': '\\223',  # left double quote  "
    '\u201d': '\\224',  # right double quote "
    '\u2013': '\\226',  # en dash
    '\u2014': '\\227',  # em dash
    '\u2026': '\\205',  # ellipsis
}


def curlify(s):
    """Convert straight quotes to typographic (curly) quotes by context."""
    out = []
    n = len(s)
    for i, c in enumerate(s):
        if c == '"':
            prev = s[i - 1] if i > 0 else ' '
            out.append('\u201d' if (prev not in ' ([{\t' and prev != '') else '\u201c')
        elif c == "'":
            prev = s[i - 1] if i > 0 else ' '
            # apostrophe if between letters (don't, it's), else opening/closing
            if prev.isalpha() or prev.isdigit():
                out.append('\u2019')
            elif prev in ' ([{':
                out.append('\u2018')
            else:
                out.append('\u2019')
        else:
            out.append(c)
    return ''.join(out)


def sanitize(s):
    # Keep unicode (curly quotes, dashes) so wrapping/width use real glyph widths.
    # The WinAnsi byte mapping happens later, inside esc().
    return curlify(s)


class PDF:
    def __init__(self):
        self.objs = []
        self.pages = []

    def add_obj(self, body):
        self.objs.append(body)
        return len(self.objs)

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
        f_reg = self.add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>')
        f_bold = self.add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>')
        f_ital = self.add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic /Encoding /WinAnsiEncoding >>')

        resources = b'<< /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >>' % (f_reg, f_bold, f_ital)
        page_obj_nums = []
        for content_num in self.pages:
            body = (
                b'<< /Type /Page /Parent __PARENT__ 0 R '
                b'/MediaBox [0 0 %d %d] /Resources %s /Contents %d 0 R >>'
                % (PAGE_W, PAGE_H, resources, content_num)
            )
            page_obj_nums.append(self.add_obj(body))

        kids = b' '.join(b'%d 0 R' % n for n in page_obj_nums)
        pages_num = self.add_obj(b'<< /Type /Pages /Kids [%s] /Count %d >>' % (kids, len(page_obj_nums)))
        for n in page_obj_nums:
            self.objs[n - 1] = self.objs[n - 1].replace(b'__PARENT__', b'%d' % pages_num)
        catalog_num = self.add_obj(b'<< /Type /Catalog /Pages %d 0 R >>' % pages_num)

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
        out.append(b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n'
                   % (n + 1, catalog_num, xref_pos))
        with open(path, 'wb') as fh:
            fh.write(b''.join(out))


MARGIN = 60
BLACK = (0, 0, 0)


def col(c):
    return '%.3f %.3f %.3f' % c


def draw_line(s, txt, x, y, size, bold=False, italic=False):
    font = '/F2' if bold else ('/F3' if italic else '/F1')
    s.append('BT %s %d Tf %d %.1f Td (%s) Tj ET' % (font, size, x, y, esc(txt)))


def render_content_slide(slide):
    s = []
    # white background
    s.append('1 1 1 rg 0 0 %d %d re f' % (PAGE_W, PAGE_H))
    s.append('0 0 0 rg')  # default text black

    max_w = PAGE_W - 2 * MARGIN

    # Centered bold title near top
    title = sanitize(slide['title'])
    ty = PAGE_H - 80
    for ln in wrap(title, 30, max_w, bold=True):
        w = text_width(ln, 30, bold=True)
        draw_line(s, ln, (PAGE_W - w) / 2, ty, 30, bold=True)
        ty -= 38

    y = ty - 30
    body_size = slide.get('body_size', 17)

    for block in slide['blocks']:
        kind = block[0]
        if kind == 'bullet':
            _, txt, opts = block
            size = opts.get('size', body_size)
            indent = opts.get('indent', 0)
            lines = wrap(sanitize(txt), size, max_w - 20 - indent)
            # bullet marker "-" style like reference deck uses "•"; use bullet char
            draw_line(s, '\x95', MARGIN + indent, y, size)  # 0x95 = bullet in WinAnsi
            for j, ln in enumerate(lines):
                draw_line(s, ln, MARGIN + indent + 16, y, size)
                y -= size + 7
            y -= 8
        elif kind == 'plain':
            _, txt, opts = block
            size = opts.get('size', body_size)
            italic = opts.get('italic', False)
            indent = opts.get('indent', 0)
            for ln in wrap(sanitize(txt), size, max_w - indent, bold=False):
                draw_line(s, ln, MARGIN + indent, y, size, italic=italic)
                y -= size + 7
            y -= 8
        elif kind == 'space':
            y -= block[1]
    return '\n'.join(s)


def render_title_slide(slide):
    s = []
    s.append('1 1 1 rg 0 0 %d %d re f' % (PAGE_W, PAGE_H))
    s.append('0 0 0 rg')
    # Big centered title, vertically middle-ish
    lines = []
    for part in slide['title_lines']:
        lines.extend(wrap(sanitize(part), 40, PAGE_W - 120, bold=False))
    total_h = len(lines) * 50
    y = PAGE_H / 2 + total_h / 2 + 40
    for ln in lines:
        w = text_width(ln, 40)
        draw_line(s, ln, (PAGE_W - w) / 2, y, 40)
        y -= 50
    # subtitle
    y -= 30
    for sub in slide.get('subtitle', []):
        txt = sanitize(sub)
        w = text_width(txt, 18)
        draw_line(s, txt, (PAGE_W - w) / 2, y, 18)
        y -= 26
    # bottom-right name/id
    if slide.get('footer'):
        txt = sanitize(slide['footer'])
        w = text_width(txt, 16)
        draw_line(s, txt, PAGE_W - MARGIN - w, 50, 16)
    return '\n'.join(s)


# --- content helpers ---
def B(txt, **o):     return ('bullet', txt, o)
def P(txt, **o):     return ('plain', txt, o)
def SP(h):           return ('space', h)


slides = []

# 1 — Title
slides.append({'kind': 'title',
    'title_lines': ['Trying to Think', 'with Emily Dickinson'],
    'subtitle': ['A reading of Jed Deppman (2005),',
                 'The Emily Dickinson Journal 14.1: 84-103'],
    'footer': 'So Yong-woon 202655100'})

# 2 — Contents
slides.append({'title': 'Contents', 'blocks': [
    B('The critical debate: mystic or thinker?'),
    B('The thesis and its statistical evidence'),
    B('Theoretical framework: postmodernism and the Kantian sublime'),
    B('The origin of "trying" and the Higginson letters'),
    B('Defining the "try-to-think" poem'),
    B('Close reading: "I tried to think a lonelier Thing" (Fr570)'),
    B('Critical assessment and my position'),
    B('Conclusion and discussion'),
]})

# 3
slides.append({'title': 'Two Epigraphs: The Central Tension', 'blocks': [
    P('"Why not an \'eleventh hour\' in the life of the mind as well as such an one in the life of the soul..."'),
    P('-- Dickinson to Austin, 1851 (L44)', indent=20),
    SP(6),
    P('"the more consciousness, the more intense the despair."'),
    P('-- Kierkegaard, Sickness unto Death', indent=20),
    SP(10),
    B('Dickinson: thinking is an existential drama, equal to the soul\'s.'),
    B('Kierkegaard: deeper consciousness means deeper despair.'),
    B('The paper lives in the gap between these two claims.'),
]})

# 3
slides.append({'title': 'The Critical Debate', 'blocks': [
    P('The received view (what Deppman opposes):'),
    B('Dickinson privileges emotional and physical response over clarity of thought.'),
    B('Peterson: her impassioned poems become "a series of ecstatic assertions, an abandonment to excess verging on mental unbalance" (500).'),
    SP(6),
    P('Deppman\'s entry point:'),
    B('Her "famous opacity" has led readers to treat affect as primary.'),
    B('He will "argue the opposite case."'),
]})

# 4
slides.append({'title': 'The Thesis', 'blocks': [
    P('"...I will argue the opposite case and portray her not as a mystic but as a serious thinker." (p. 85)'),
    SP(10),
    B('Not "ecstatic assertions" but "careful sequences of ideas and images."'),
    B('Not "abandonment to excess" but "thoughtful production of, and reaction to, extreme states of being."'),
    SP(6),
    B('Goal: how Dickinson conceived the activity of thinking, and "how writing poetry helped her think."'),
]})

# 5
slides.append({'title': 'Evidence 1: Word Statistics', 'blocks': [
    P('Rosenbaum Concordance (1955 Johnson edition):'),
    B('Feeling-words: feel 39, felt 35, feels 16, feeling 8; body 10, bodies 1.'),
    B('Thinking-words: thought 69, think 43, know 230, knew 80; mind 79, brain 26.'),
    SP(6),
    B('"know" is the 4th most common verb overall (after be, be able, have).'),
    B('Deppman: "much more about thought than feeling" (p. 86).'),
    B('But his own caveat: the statistics are "partial and decontextualized" (p. 86).'),
]})

# 6
slides.append({'title': 'Evidence 2: The Many Faces of Thought', 'blocks': [
    P('Thought is a "consistent as well as kaleidoscopic" topic (p. 85):'),
    B('Celebratory: "Best Things dwell out of Sight / ... Our Thought" (Fr1012)'),
    B('Cautionary: "If wrecked upon the Shoal of Thought..." (Fr1503)'),
    B('Analytic: "The Brain - is wider than the Sky -" (Fr598)'),
    B('Wild: "The Brain, within it\'s Groove / Runs evenly ... But let a Splinter swerve -" (Fr563)'),
    B('Sufficient for happiness: "The revery alone will do, / If bees are few" (Fr1779)'),
]})

# 7
slides.append({'title': 'Framework 1: Postmodern Dickinson', 'blocks': [
    B('Wolff: "artist of the age of transition" - freeing language "from the tyranny of His definitions" (429).'),
    B('Porter: the mind "explosive with signifying power but disinherited from transcendent knowledge" (7).'),
    B('Lyotard: postmodernism is "incredulity toward metanarratives."'),
    B('Derrida: Dickinson as "bricoleuse," mixing religious, literary, and scientific vocabularies.'),
    SP(6),
    B('Root condition: the tension between Lockean empiricism (her schoolbooks) and Kantian / Transcendentalist apprehension of the supersensible (p. 86).'),
]})

# 8
slides.append({'title': 'Framework 2: The Kantian Sublime', 'blocks': [
    P('The engine of the whole paper:'),
    B('1. Reason conceives something conceivable but unpresentable (infinity, death).'),
    B('2. Reason demands an adequate image.'),
    B('3. Imagination tries and fails.'),
    B('4. The mind repeats the try; from this the sublime emerges.'),
    SP(4),
    B('Lyotard: "invent allusions to the conceivable which cannot be presented" (Postmodern 81).'),
    B('Key concession: Dickinson "did not read Kant" (p. 87) - a shared attitude, not influence.'),
]})

# 9
slides.append({'title': 'The Origin of "Trying" (L10, 1846)', 'blocks': [
    P('At age fifteen, Dickinson tries to think her own death:'),
    P('"I cannot imagine with the farthest stretch of my imagination my own death scene... I cannot realize that the grave will be my last home..."'),
    SP(8),
    B('The refrain: "I cannot imagine ... I cannot realize ... nor can I realize ..."'),
    B('The mind "stretches, fails, realizes it fails, regroups, rewords, and reaches its limit again" (p. 88).'),
    B('Core formula: "she cannot think death or Eternity ... but she cannot not think them either."'),
]})

# 10
slides.append({'title': 'Evidence 3: The Higginson Letters', 'blocks': [
    P('Writing understood as thought:'),
    B('1862 (L260): "Are you too deeply occupied to say if my Verse is alive?"'),
    B('The bind (L260): "The Mind is so near itself - it cannot see, distinctly - and I have none to ask -."'),
    B('Writing as therapy (L261): "I had a terror ... and so I sing, as the Boy does by the Burying Ground - because I am afraid."'),
    B('Thought over language (L261): "While my thought is undressed ... but when I put them in the Gown - they look alike, and numb."'),
    B('To the end (L1042): "bereft of Book and Thought, by the doctor\'s reproof."'),
]})

# 11
slides.append({'title': 'Defining the "Try-to-Think" Poem', 'blocks': [
    B('Purpose: to force the mind to satisfy reason\'s unsatisfiable demand for a complete image.'),
    B('"the try is usually serious, the goal explicitly stated, ... emphasis squarely on the willful movements of thought."'),
    B('They are "precisely sequenced, if difficult, thought experiments" - readers repeat the steps.'),
    SP(8),
    P('Examples: "Of Death I try to think like this" (Fr1588); "The nearest Dream recedes" (Fr304B); "I think To Live - may be a Bliss" (Fr757).'),
]})

# 12
slides.append({'title': 'Close Reading 1: Fr570 and the Dilemma', 'body_size': 15, 'blocks': [
    P('"I tried to think a lonelier Thing / Than any I had seen - / Some Polar Expiation - An Omen in the Bone / Of Death\'s tremendous nearness - ... I plucked at our Partition - ... I almost strove to clasp his Hand, / Such Luxury - it grew - / That as Myself - could pity Him - / Perhaps he - pitied me -"'),
    SP(6),
    P('The interpretive dilemma (p. 94):'),
    B('Proactive? - a "virtuoso attempt to conceptualize an extreme human possibility."'),
    B('Reactive? - an attempt "to knead it, battle it, alter it, realize it, or just survive it through thought."'),
    B('Deppman chooses: reactive.'),
]})

# 13
slides.append({'title': 'Close Reading 2: Tracking the Steps', 'blocks': [
    B('1. Naming the "Thing" as two quiddities:'),
    B('"Some Polar Expiation" - expiation plus polar expedition: radical exile from self, culture, nature.', indent=20),
    B('"An Omen in the Bone / Of Death\'s tremendous nearness" - anticipatory; near in time and space.', indent=20),
    B('2. Borrowing a "Duplicate" - a spirit "Of Heavenly Love - forgot -": the "smallest possible unit of imagined community."'),
    B('3. "Within the Clutch of Thought" - undecidable: reachable by thought, or made only of thought (fabricated)?'),
    B('4. "our Partition" - the possessive forms "a we": bridge and barrier between living self and dead twin.'),
]})

# 14
slides.append({'title': 'Close Reading 3: The Paradoxical Close', 'blocks': [
    P('"I almost strove to clasp his Hand, / Such Luxury - it grew - / That as Myself - could pity Him - / Perhaps he - pitied me -"'),
    SP(8),
    B('Two God-forsaken souls in "Opposing Cells" - "a chilling scene reminiscent of Beckett\'s Godot."'),
    B('Deppman hears an elided phrase: "Such Luxury - it grew [- to think]."'),
    B('So consolation comes from the experimental force of thought itself.'),
    B('But: "a fragile state and a momentary victory" - how long can it console?'),
]})

# 15
slides.append({'title': 'Critical Assessment: Strengths', 'blocks': [
    B('Methodological rigor - grounds a large claim in concordance data (p. 86), not impression. A falsifiable move.'),
    B('Genuine integration - the letters (L10, L260, L261) function as evidence of a poetics, not decorative biography.'),
    B('A generative concept - the "try-to-think poem" names a real, repeatable pattern, applicable beyond his sample.'),
    B('Reframes opacity as method - difficulty is the trace of a mind at work, not failure or excess.'),
]})

# 16
slides.append({'title': 'Critical Assessment: My Position', 'blocks': [
    P('Claim: the thesis is self-undermining - and that is its most interesting result.'),
    SP(6),
    B('Deppman picks thought over feeling. Yet his own reading of Fr570 runs on affect: "desperate," "chilling," "sickening loneliness," writing as "thought\'s psychotherapeutic response to troubling emotion" (p. 90).'),
    B('If the "try" matters only because the loneliness is unbearable, then thought and feeling are inseparable - the binary collapses.'),
    B('So the real achievement is the opposite of the stated one: thinking is an emotional act.'),
    B('Further bait: "Kant without Kant" (p. 87); the circularity of the genre; Muldoon\'s Civil War reading (note 18).'),
]})

# 17
slides.append({'title': 'Conclusion and Discussion Questions', 'blocks': [
    B('Deppman: these are poems in which she "tried to help or save herself by representing her own efforts to help or save herself" (p. 100).'),
    B('To join the poem is to risk "experiencing a loneliness we cannot sound."'),
    B('Return to Kierkegaard: thought is both consolation and risk.'),
    SP(8),
    P('Discussion questions:'),
    B('1. Does the thought/feeling binary survive Deppman\'s own close reading?'),
    B('2. Is the Kantian sublime valid for a poet who never read Kant?'),
    B('3. Is "try-to-think" a discovered genre or a critic\'s construct?'),
    B('4. Whose reading of Fr570 convinces you - Deppman\'s or Muldoon\'s?'),
]})


pdf = PDF()
for sl in slides:
    if sl.get('kind') == 'title':
        pdf.add_page(render_title_slide(sl))
    else:
        pdf.add_page(render_content_slide(sl))
pdf.build('/projects/sandbox/dickinson_presentation.pdf')
print('Wrote dickinson_presentation.pdf with %d slides (Times serif, minimal style)' % len(slides))
