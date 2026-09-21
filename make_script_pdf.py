#!/usr/bin/env python3
"""
Generate a PDF of the 25-minute presentation script + speaker notes,
corresponding to the final 18-slide deck. Portrait A4-ish, Times serif,
pure standard library (no external deps).
"""

import zlib

PAGE_W, PAGE_H = 612, 792  # US Letter portrait

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
TIMES_BOLD = dict(TIMES)
TIMES_BOLD.update({
    'a':500,'b':556,'c':444,'d':556,'e':444,'f':333,'g':500,'h':556,'i':278,
    'j':333,'k':556,'l':278,'m':833,'n':556,'o':500,'p':556,'q':556,'r':444,
    's':389,'t':333,'u':556,'v':500,'w':722,'x':500,'y':500,'z':444,
    'A':722,'B':667,'C':722,'D':722,'E':667,'F':611,'G':778,'H':778,'M':944,
    'N':722,'O':778,'P':611,'R':722,'S':556,'T':667,'W':1000,
})


def cw(ch, size, bold=False):
    return (TIMES_BOLD if bold else TIMES).get(ch, 500) / 1000.0 * size


def tw(s, size, bold=False):
    return sum(cw(c, size, bold) for c in s)


def wrap(text, size, max_w, bold=False):
    out = []
    for para in text.split('\n'):
        if para == '':
            out.append('')
            continue
        words = para.split(' ')
        cur = ''
        for w in words:
            trial = w if not cur else cur + ' ' + w
            if tw(trial, size, bold) <= max_w or not cur:
                cur = trial
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out


def esc(s):
    s = s.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')
    repl = {'\u2018':'\\221','\u2019':'\\222','\u201c':'\\223','\u201d':'\\224',
            '\u2013':'\\226','\u2014':'\\227','\u2026':'\\205','\u2022':'-',
            '\u2192':'->','\u2011':'-'}
    for u,c in repl.items():
        s = s.replace(u,c)
    return ''.join(ch if ord(ch)<256 else '?' for ch in s)


def curly(s):
    out=[]; 
    for i,c in enumerate(s):
        if c=='"':
            prev=s[i-1] if i>0 else ' '
            out.append('\u201d' if prev not in ' ([{\t' else '\u201c')
        elif c=="'":
            prev=s[i-1] if i>0 else ' '
            out.append('\u2019' if (prev.isalpha() or prev.isdigit()) else ('\u2018' if prev in ' ([{' else '\u2019'))
        else: out.append(c)
    return ''.join(out)


class PDF:
    def __init__(self): self.objs=[]; self.pages=[]
    def add(self,b): self.objs.append(b); return len(self.objs)
    def page(self,cs):
        comp=zlib.compress(cs.encode('latin-1','replace'))
        n=self.add(b'<< /Length %d /Filter /FlateDecode >>\nstream\n'%len(comp)+comp+b'\nendstream')
        self.pages.append(n)
    def build(self,path):
        fr=self.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>')
        fb=self.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>')
        fi=self.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic /Encoding /WinAnsiEncoding >>')
        res=b'<< /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >>'%(fr,fb,fi)
        pn=[]
        for c in self.pages:
            pn.append(self.add(b'<< /Type /Page /Parent __P__ 0 R /MediaBox [0 0 %d %d] /Resources %s /Contents %d 0 R >>'%(PAGE_W,PAGE_H,res,c)))
        kids=b' '.join(b'%d 0 R'%n for n in pn)
        pnode=self.add(b'<< /Type /Pages /Kids [%s] /Count %d >>'%(kids,len(pn)))
        for n in pn: self.objs[n-1]=self.objs[n-1].replace(b'__P__',b'%d'%pnode)
        cat=self.add(b'<< /Type /Catalog /Pages %d 0 R >>'%pnode)
        out=[b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n']; offs=[]; pos=len(out[0])
        for i,b in enumerate(self.objs,1):
            o=b'%d 0 obj\n'%i+b+b'\nendobj\n'; offs.append(pos); out.append(o); pos+=len(o)
        xp=pos; n=len(self.objs)
        xr=[b'xref\n',b'0 %d\n'%(n+1),b'0000000000 65535 f \n']
        for o in offs: xr.append(b'%010d 00000 n \n'%o)
        out+=xr; out.append(b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n'%(n+1,cat,xp))
        open(path,'wb').write(b''.join(out))


MARGIN=60
LEAD_H1=20; LEAD_H2=16; LEAD_BODY=14

class Writer:
    def __init__(self,pdf): self.pdf=pdf; self.s=[]; self.y=0; self.newpage()
    def newpage(self):
        if self.s: self.pdf.page('\n'.join(self.s))
        self.s=['1 1 1 rg 0 0 %d %d re f'%(PAGE_W,PAGE_H),'0 0 0 rg']
        self.y=PAGE_H-60
    def ensure(self,h):
        if self.y-h < 60: self.newpage()
    def line(self,txt,size,font='/F1',gap=6,indent=0,color=None):
        maxw=PAGE_W-2*MARGIN-indent
        bold = font=='/F2'
        for ln in wrap(curly(txt),size,maxw,bold=bold):
            self.ensure(size+gap)
            if color: self.s.append('%s rg'%color)
            self.s.append('BT %s %d Tf %d %.1f Td (%s) Tj ET'%(font,size,MARGIN+indent,self.y,esc(ln)))
            if color: self.s.append('0 0 0 rg')
            self.y-=size+gap
    def gap(self,h): self.y-=h
    def rule(self):
        self.ensure(12)
        self.s.append('0.6 0.6 0.6 RG 0.8 w %d %.1f m %d %.1f l S'%(MARGIN,self.y,PAGE_W-MARGIN,self.y))
        self.y-=12
    def finish(self):
        if self.s: self.pdf.page('\n'.join(self.s))


ACCENT='0 0 0'
GRAY='0 0 0'


# ---- content ----
pdf=PDF(); w=Writer(pdf)

# Cover
w.gap(180)
for ln in ['Trying to Think','with Emily Dickinson']:
    wln=tw(ln,30,True); w.s.append('BT /F2 30 Tf %.1f %.1f Td (%s) Tj ET'%((PAGE_W-wln)/2,w.y,esc(ln))); w.y-=38
w.gap(10)
for ln in ['25-Minute Presentation Script + Speaker Notes',
           'A reading of Jed Deppman (2005),',
           'The Emily Dickinson Journal 14.1: 84-103',
           '','So Yong-woon 202655100']:
    wln=tw(ln,14); w.s.append('%s rg BT /F1 14 Tf %.1f %.1f Td (%s) Tj ET 0 0 0 rg'%(GRAY,(PAGE_W-wln)/2,w.y,esc(ln))); w.y-=22
w.newpage()

# Argument-flow summary page
w.line('The Argument in One Breath',16,'/F2',gap=10,color=ACCENT)
w.rule()
w.line("Refute the mystic reading -> prove her obsession with thought via word-statistics -> theorize it through Kant's sublime and the postmodern -> confirm \"writing = thinking\" via the Higginson letters -> define the \"try-to-think\" poem -> demonstrate it through a close reading of Fr570 -> conclude that thought is both consolation AND risk.",12,'/F1',gap=6)
w.gap(6)
w.line("My through-line (the critique):",12,'/F2',gap=6,color=ACCENT)
w.line("Deppman sets up thought VS feeling and picks thought -- but his own reading of Fr570 runs on affect. If the \"try\" matters only because the loneliness is unbearable, thought and feeling cannot be separated. So the essay's real achievement is the opposite of its stated one: thinking is an emotional act. The thesis is self-undermining -- and that is what makes it worth reading.",12,'/F1',gap=6)
w.gap(6)
w.line("Bookend: open with the Kierkegaard/Dickinson tension (Slide 3); close by returning to it (Slide 17) and to \"I dwell in Possibility\" (Slide 18).",12,'/F1',gap=6)
w.newpage()

def slide(num, title, target, script, notes):
    w.ensure(120)
    # slide header
    w.s.append('%s rg'%ACCENT)
    w.s.append('BT /F2 15 Tf %d %.1f Td (%s) Tj ET'%(MARGIN,w.y,esc('SLIDE %s  |  %s'%(num,target))))
    w.s.append('0 0 0 rg'); w.y-=22
    w.line(title,16,'/F2',gap=8)
    w.rule()
    w.line('SCRIPT',11,'/F2',gap=6)
    for para in script:
        w.line(para,12,'/F1',gap=6); w.gap(4)
    w.gap(4)
    w.line('SPEAKER NOTES',11,'/F2',gap=6,color=GRAY)
    for n in notes:
        w.line('- '+n,11,'/F1',gap=5,indent=8)
    w.gap(16)


slide('1','Title','0:45',
 ["Good afternoon. Today I'm looking at Jed Deppman's 2005 essay, \"Trying to Think with Emily Dickinson,\" from The Emily Dickinson Journal. The title is the key. Notice he doesn't say \"thinking with Dickinson\" -- he says *trying* to think. That one word, \"trying,\" holds the whole argument together. So I'll do two things today: first, lay out his argument clearly and fairly; and second, push back on it -- I'll argue that the essay quietly works against its own main claim, and that this is actually what makes it worth reading."],
 ["Open with energy; the hook is the word \"trying.\"",
  "Preview that you will both explain AND push back.",
  "Don't rush -- set a calm pace for a 25-min talk."])

slide('2','Contents','0:50',
 ["Here's the plan. We start with two epigraphs that set up the central tension. Then the big debate -- is Dickinson a poet of feeling, or a serious thinker? After that: his thesis and the word-count evidence behind it; the theory he uses -- postmodernism and Kant's idea of the sublime; where this \"trying\" comes from, in her letters to Higginson; his key idea, the \"try-to-think\" poem; then a close reading of one poem, \"I tried to think a lonelier Thing\"; and finally my own take and some questions for us. It's a lot, but everything builds toward that one poem and one closing point."],
 ["Gesture through the list; don't read every word.",
  "Signal that the close reading (Fr570) is the heart."])

slide('3','Two Epigraphs: The Central Tension','1:20',
 ["Deppman starts with two epigraphs, and they set up everything. The first is Dickinson writing to her brother Austin in 1851: \"Why not an 'eleventh hour' in the life of the mind as well as such an one in the life of the soul?\" The \"eleventh hour\" is a religious image -- your last chance to be saved. What she's doing is moving that life-or-death drama from the soul over to the mind. In other words, for her, thinking is just as high-stakes as whether your soul is saved.",
  "The second is from Kierkegaard: \"the more consciousness, the more intense the despair.\" That's the dark side of the same idea -- the more aware you are, the more you can suffer. So even before the argument starts, there's a tension in the room: thinking matters enormously to Dickinson, but thinking also hurts. Hold on to that -- we come back to Kierkegaard right at the end."],
 ["Read both epigraphs aloud, slowly.",
  "Flag the Kierkegaard line -- it comes back in the conclusion (bookend).",
  "This tension is the seed of your later critique (thought vs. feeling)."])

slide('4','The Critical Debate','1:30',
 ["So why make this argument at all? Because Deppman is going against a long-standing way of reading Dickinson. The usual view treats her as a poet of feeling -- of ecstasy and physical sensation. The sharpest version comes from Margaret Peterson, quoted here: her most passionate poems turn into \"a series of ecstatic assertions, an abandonment to excess verging on mental unbalance.\" In plain terms: at her most intense, Dickinson supposedly stops thinking and just erupts.",
  "Deppman's move is to take that famous difficulty -- how hard her poems are to read -- and flip it. Where others see emotional overload, he wants to see careful, disciplined thinking. So he says he'll \"argue the opposite case and portray her not as a mystic but as a serious thinker.\""],
 ["Set up the boxing match: mystic vs. thinker.",
  "Note Peterson is quoted via Deppman (qtd. in Deppman 84).",
  "The red 'not as a mystic' / blue 'serious thinker' is the pivot."])

slide('5',"Deppman's Thesis",'1:20',
 ["Here's the thesis in his own words: he'll \"portray her not as a mystic but as a serious thinker.\" Notice the two contrasts. Instead of \"ecstatic assertions,\" he sees \"careful sequences of ideas and images.\" Instead of \"abandonment to excess,\" he sees \"thoughtful production of, and reaction to, extreme states of being\" -- meaning she isn't losing control, she's carefully working through hard experiences.",
  "So the claim is strong: the act of thinking itself is the real subject of her poems. His goal -- and I'd underline this line -- is to show \"how writing poetry helped her think.\" But keep one question in mind as we go: can you really separate thought from feeling? I don't think you can -- and I don't think his own evidence lets him either."],
 ["This is THE thesis sentence -- read it verbatim.",
  "Plant your counter-question here (thought/feeling inseparable).",
  "Color: the thesis quote is Deppman (blue)."])

slide('6','The Statistical Evidence','1:30',
 ["Deppman's first move is nicely concrete: he actually counts. Using the Rosenbaum Concordance, on the feeling side -- feel 39, felt 35, feels 16, feeling 8; body only 10. On the thinking side, much bigger numbers -- thought 69, think 43, and \"know\" 230 times. \"Know\" is basically the fourth most common verb in her whole body of work. \"Mind\" 79, \"brain\" 26.",
  "The gap is hard to ignore, and Deppman concludes her poetry is \"much more about thought than feeling.\" This is the strongest part of the essay -- it's a claim you could actually check. But -- and this matters for later -- he himself admits the numbers are \"partial and decontextualized.\" And he's right: counting words tells you what she talks about, not how she feels about it, and definitely not that thought is somehow the opposite of feeling."],
 ["Emphasize 230 vs. 39 -- the striking number.",
  "The 'partial and decontextualized' caveat is a seed for Slide 16.",
  "Numbers themselves are neutral (black); Deppman's claim is blue."])

slide('7','The Kaleidoscope of Thought','1:20',
 ["Deppman then shows that thought isn't just frequent -- it's a \"consistent as well as kaleidoscopic\" topic, meaning she looks at it from many different angles. Sometimes she celebrates it: \"Best Things dwell out of Sight ... Our Thought.\" Sometimes she warns about it: \"If wrecked upon the Shoal of Thought.\" Sometimes she measures it: \"The Brain is wider than the Sky.\" Sometimes it turns wild: \"The Brain, within its Groove ... But let a Splinter swerve.\" And sometimes it's enough to make you happy on its own: \"The revery alone will do, if bees are few.\"",
  "The point is simple: thought isn't a side effect in her poems -- it's a subject she keeps turning over on purpose."],
 ["Read one or two poem fragments aloud for texture.",
  "The phrase 'kaleidoscopic' is Deppman's (blue); poems are Dickinson (green)."])

slide('8','Postmodern Dickinson?','1:30',
 ["Deppman then connects Dickinson to some big names in theory. Wolff calls her an \"artist of the age of transition,\" someone freeing language \"from the tyranny of His definitions\" -- that is, from God's authority. Porter describes her mind as \"explosive with signifying power but disinherited from transcendent knowledge\" -- huge energy, but no stable God to hold onto. He borrows Lyotard's line about the postmodern -- \"incredulity toward metanarratives,\" meaning distrust of any big all-explaining system -- and Derrida's word \"bricoleuse,\" someone who mixes and reuses whatever vocabularies are around -- religious, literary, scientific.",
  "The root of all this, he says, is one tension: the down-to-earth empiricism of her schoolbooks (Locke) versus the Kantian, Transcendentalist idea that the mind can reach beyond the senses. Dickinson sits right in that gap -- and it's the Kantian side that becomes the engine of the whole essay."],
 ["Move briskly -- this is a list of critics; don't linger.",
  "All these are quoted from Deppman 86 (note the footer).",
  "Bridge to next slide: 'and here is that Kantian engine.'"])

slide('9','The Kantian Sublime','1:40',
 ["So here's that engine -- the Kantian sublime, the same idea Lyotard turns into the postmodern condition. It works in four steps. One: the mind thinks of something it can conceive but can't picture -- infinity, death. Two: it demands an image that fits. Three: the imagination tries to give one -- and fails; the thing is just too big to picture. Four: the mind keeps trying anyway, and out of that struggle the feeling of the sublime is born. Lyotard puts it as the artist's job: to \"invent allusions to the conceivable which cannot be presented\" -- basically, to gesture at what can't be shown directly.",
  "Notice the word feeling in step four -- even in the theory, the sublime is an experience, not just a thought. And here's the honest catch: Deppman admits Dickinson \"did not read Kant.\" So he's claiming a shared attitude, not actual influence. Keep that question open: if she never read Kant, is the sublime something he finds in the poems, or something he brings to them?"],
 ["Draw or trace the try -> fail -> repeat loop.",
  "Stress 'did not read Kant' -- it returns in Slide 16 as 'Kant without Kant.'",
  "The word 'feeling' in step 4 supports your thesis-collapse argument."])

slide('10','The Higginson Letters (Letters with Higginson)','1:30',
 ["Deppman's next evidence is her letters to Higginson -- the only real literary exchange she kept up. His claim: she treated writing AS thinking. In 1862 she asks: \"Are you too deeply occupied to say if my Verse is alive?\" -- not whether it's pretty or correct, but alive: is the thought in it living? And she explains why she can't tell on her own: \"The Mind is so near itself -- it cannot see, distinctly -- and I have none to ask.\" In other words, the mind is too close to itself to judge itself clearly.",
  "But look at WHY she says she writes: \"I had a terror ... and so I sing, as the Boy does by the Burying Ground -- because I am afraid\" -- she writes the way a scared kid sings walking past a graveyard. And Deppman himself calls her writing \"thought's psychotherapeutic response to troubling emotion\" -- plainly, thinking she uses to cope with painful feelings. So even while he's arguing for thought, he tells us the thinking is there to manage feeling. And right to the end, when she's ill, what she misses is \"Book and Thought.\""],
 ["Highlight the 'therapy' quote -- your key evidence for Slide 16.",
  "All quotes here are Dickinson (green).",
  "Note her frustration when Higginson replies about form, not thought."])

slide('11','Defining the "Try-to-Think" Poem','1:10',
 ["All of this leads to Deppman's main idea: the \"try-to-think\" poem. The point of such a poem is to push the mind to do something it can't quite do -- to give a full picture of something that can't really be pictured. His description: \"the try is usually serious, the goal explicitly stated, ... emphasis squarely on the willful movements of thought.\" These are \"precisely sequenced, if difficult, thought experiments\" -- and they ask the reader to walk through the steps too. Examples: \"Of Death I try to think like this\" and \"I think To Live -- may be a Bliss.\"",
  "This is a genuinely useful idea -- it names a real, repeating pattern in her work. So let's watch it play out in the poem Deppman treats as the best example of the type."],
 ["This concept is the paper's original contribution -- give it credit.",
  "But note (for Slide 16) the genre is defined FROM the poems it explains."])

slide('12','Close Reading 1: Fr570 and the Dilemma','1:40',
 ["The poem is \"I tried to think a lonelier Thing,\" from 1863. It starts with the speaker trying to name a loneliness worse than any she's known -- \"Some Polar Expiation,\" \"An Omen in the Bone / Of Death's tremendous nearness\" -- and ends, after she picks at a \"Partition,\" with: \"I almost strove to clasp his Hand, / Such Luxury -- it grew -- / That as Myself -- could pity Him -- / Perhaps he -- pitied me.\"",
  "Deppman asks a sharp question about it. Is the trying active -- a \"virtuoso attempt to conceptualize an extreme human possibility,\" like a show of skill? Or is it reactive -- a way \"to knead it, battle it, alter it, realize it, or just survive it through thought\"? He picks reactive. And that choice matters a lot: if the poem is reactive, then the pain comes first, and the thinking is the response to it. That's not thought instead of feeling -- it's thought because of feeling. Remember that."],
 ["Read the poem excerpt slowly.",
  "'Deppman chooses reactive' -- circle this; it's your pivot to Slide 16.",
  "Poem = green; the two options + 'reactive' = Deppman (blue)."])

slide('13','Close Reading 2: Tracking the Steps (Fr570)','1:50',
 ["Let's follow the steps, because this is where the reading really shines. First, the speaker tries to name the \"Thing\" -- and gives two tries. \"Some Polar Expiation\": expiation means a religious cleansing, and \"Polar\" puns on a polar expedition, so together it's about being cut off completely -- from yourself, your world, everything. Then \"An Omen in the Bone / Of Death's tremendous nearness\" -- this one looks forward: death felt as close, in both time and space.",
  "Second, she borrows a \"Duplicate\" -- another soul also \"Of Heavenly Love -- forgot\" -- what Deppman calls \"the smallest possible unit of imagined community.\" She's so alone she has to invent a fellow sufferer just to have company. Third, the key ambiguity: \"Within the Clutch of Thought\" is undecidable -- is that double real and reachable by thought, or made only of thought, just made up? The whole poem turns on this. And fourth: \"our Partition\" -- notice it's \"our,\" not \"the.\" That one small word creates a \"we\": the wall between the living speaker and her imagined dead twin becomes both a barrier and a bridge. The mind has made a relationship where there was only loneliness."],
 ["This is the heart of the talk -- show theory (Slide 9) operating on text.",
  "Green = Dickinson's words; blue = Deppman's readings ('a we' is blue!).",
  "Slow down on the 'undecidable' point -- it's the poem's hinge."])

slide('14','Close Reading 3: The Paradoxical Close (Fr570)','1:30',
 ["Now the ending -- strange and moving. The speaker and her invented double are two God-forsaken souls in \"Opposing Cells\" -- Deppman calls it \"a chilling scene reminiscent of Beckett's Godot,\" two figures who can almost, but never quite, reach each other. Then Deppman does something bold: he inserts a phrase he says is implied, reading the line as \"Such Luxury -- it grew [-- to think].\" On his reading, the strange comfort comes from the power of the thinking itself.",
  "But listen to how he describes that comfort: \"a fragile state and a momentary victory: how long can meditating on one's dead duplicate continue to console?\" And here's my point -- it's fragile exactly because it's emotional. A logical proof doesn't fade; a comforting feeling does. The ending wobbles because a mood wobbles. So the poem that's supposed to show thought winning actually ends by showing thought leaning on a feeling that won't last."],
 ["Note that '[to think]' is INSERTED -- not in the original (your critique word).",
  "The 'fragile / momentary' quote is Deppman's own -- he undermines himself.",
  "This is the bridge into your position: fragile = emotional."])

slide('15','Critical Assessment: Strengths','1:15',
 ["Before I push back, let me give the essay real credit. Four strengths. First, it's rigorous: he backs a big claim with word-count data, not just a hunch -- and that's something you can actually check, which is rare in criticism. Second, it's well integrated: the letters work as real evidence for how she wrote, not just background trivia. Third -- and this lasts the longest -- the \"try-to-think poem\" is a useful idea we can take to poems he never even mentions. Fourth, he changes how we see her difficulty: where others saw her hard poems as failure or excess, he lets us see them as the marks of a mind at work.",
  "So it's a strong, serious essay -- which is exactly why it's worth pushing on its main claim."],
 ["Be genuinely fair here -- it earns credibility for your critique.",
  "Keep this slide calm/black; save the red for Slide 16.",
  "End with the turn: 'which is why it's worth pressing.'"])

slide('16','Critical Assessment: My Position','1:50',
 ["Here's my position, plainly: the thesis works against itself -- and that's the most interesting thing about it. Deppman picks thought over feeling. But look at the words in his own close reading: he calls the scene \"chilling,\" he talks about \"sickening loneliness,\" and he defines her writing as \"thought's psychotherapeutic response to troubling emotion.\" Every one of those is a feeling word.",
  "So here's the problem: if the \"try\" only matters because the loneliness is unbearable -- and he insists the poem is reactive -- then you can't pull thought and feeling apart. The very split his essay is built on falls apart on his own evidence. So the real result is the opposite of what he set out to prove: thinking is an emotional act. And I don't think that ruins the essay -- I think it makes it truer than its own thesis.",
  "Three quick things to argue about: \"Kant without Kant\" -- is the sublime something he finds in her, or something he puts on her? The genre feels a little circular -- it's defined from the same poems it then explains. And Muldoon's Civil War reading of the poem, which Deppman turns down -- worth questioning."],
 ["This is the climax -- commit fully to the stance.",
  "The affect words are Deppman's own (blue) -- that's the proof.",
  "Deliver 'thinking is an emotional act' slowly; it's your core sentence.",
  "Invite disagreement openly."])

slide('17','Conclusion & Discussion Questions','1:15',
 ["Let me pull it together. Deppman ends honestly: we never really know if Dickinson managed to think what she tried to think. What we do know is that these are poems where she \"tried to help or save herself by representing her own efforts to help or save herself.\" And to read them, he says, is to risk \"experiencing a loneliness we cannot sound\" -- a loneliness we can't measure the depth of.",
  "And that brings us back to Kierkegaard -- the more consciousness, the more despair. In Dickinson, thought is never just comfort; it's comfort AND risk at the same time. Which is exactly why I've argued you can't cleanly split her thinking from her feeling. So, four questions for us. Does the thought-versus-feeling split survive Deppman's own close reading? Is the Kantian sublime a fair frame for a poet who never read Kant? Is \"try-to-think\" a genre he discovered, or one he built? And does Kierkegaard's idea -- more consciousness, more despair -- actually hold for Dickinson's poetry?"],
 ["Return to Kierkegaard -- name the bookend explicitly.",
  "End on the questions, not a summary -- hand the floor over.",
  "Q4 was changed to Kierkegaard (not Muldoon) to close the circle."])

slide('18','"I dwell in Possibility --"','0:40',
 ["I'll end where Dickinson might want us to -- not on a conclusion, but on an opening. Her line: \"I dwell in Possibility.\" I've argued that Deppman sets out to prove she's a thinker, not a feeler, and that his own reading erases that line -- because in Dickinson, to think the unthinkable is to feel it. But erasing that line doesn't shrink her; it opens her up. If her poems are experiments we're invited to try, not answers we're handed, then reading her is never finished -- it's a place we live in, not a problem we solve. That's why she \"dwells in Possibility\" -- and why, a century later, we're still trying to think with Emily Dickinson. Thank you."],
 ["Slow, warm close. Let the final line land.",
  "Then open Q&A."])

w.finish()
pdf.build('/projects/sandbox/dickinson_presentation_script.pdf')
print('Wrote dickinson_presentation_script.pdf')
