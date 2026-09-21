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


ACCENT='0.13 0.30 0.52'
GRAY='0.35 0.35 0.35'


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
    w.line('SCRIPT',11,'/F2',gap=6,color=ACCENT)
    for para in script:
        w.line(para,12,'/F1',gap=6); w.gap(4)
    w.gap(4)
    w.line('SPEAKER NOTES',11,'/F2',gap=6,color=GRAY)
    for n in notes:
        w.line('- '+n,11,'/F1',gap=5,indent=8)
    w.gap(16)


slide('1','Title','0:45',
 ["Good afternoon. Today I'm presenting Jed Deppman's 2005 essay, \"Trying to Think with Emily Dickinson,\" from The Emily Dickinson Journal. The title itself is the key: Deppman does not say \"thinking with Dickinson\" but *trying* to think. That word \"trying\" carries the whole argument. My aim is twofold: to reconstruct his argument fairly, and then to argue that it quietly undermines its own central claim -- and that this is exactly what makes it worth reading."],
 ["Open with energy; the hook is the word \"trying.\"",
  "Preview that you will both explain AND push back.",
  "Don't rush -- set a calm pace for a 25-min talk."])

slide('2','Contents','0:50',
 ["Here is our road map. We begin with two epigraphs that frame the central tension. Then the critical debate -- is Dickinson a mystic of feeling, or a serious thinker? From there: the thesis and its statistical evidence; the theoretical framework of postmodernism and the Kantian sublime; the origin of \"trying\" in the Higginson letters; the definition of the \"try-to-think\" poem; a close reading of \"I tried to think a lonelier Thing\"; and finally my critical assessment and conclusion. It all builds toward that one poem and one closing claim."],
 ["Gesture through the list; don't read every word.",
  "Signal that the close reading (Fr570) is the heart."])

slide('3','Two Epigraphs: The Central Tension','1:20',
 ["Deppman opens with two epigraphs, and they frame everything. First, Dickinson to her brother Austin in 1851: \"Why not an 'eleventh hour' in the life of the mind as well as such an one in the life of the soul?\" The \"eleventh hour\" is a religious image -- the last chance for salvation. Dickinson transfers that drama from the soul to the mind. For her, thinking carries the same existential stakes as the fate of the soul.",
  "Second, Kierkegaard: \"the more consciousness, the more intense the despair.\" This is the darker side -- greater consciousness can mean greater suffering. So before the argument even begins, a tension is planted: thinking matters enormously, yet thinking hurts. Hold on to that -- we return to Kierkegaard at the very end."],
 ["Read both epigraphs aloud, slowly.",
  "Flag the Kierkegaard line -- it comes back in the conclusion (bookend).",
  "This tension is the seed of your later critique (thought vs. feeling)."])

slide('4','The Critical Debate','1:30',
 ["Why make this argument at all? Because Deppman pushes against an established reading. The traditional view treats Dickinson as a poet of feeling -- of ecstasy and physical sensation. Its sharpest form comes from Margaret Peterson, quoted here: her impassioned poems become \"a series of ecstatic assertions, an abandonment to excess verging on mental unbalance.\" Essentially: at her most intense, Dickinson stops thinking and simply erupts.",
  "Deppman's move is to take that famous opacity -- the notorious difficulty -- and reinterpret it. Where others see emotional excess, he wants disciplined intellectual work. So he announces he will \"argue the opposite case and portray her not as a mystic but as a serious thinker.\""],
 ["Set up the boxing match: mystic vs. thinker.",
  "Note Peterson is quoted via Deppman (qtd. in Deppman 84).",
  "The red 'not as a mystic' / blue 'serious thinker' is the pivot."])

slide('5',"Deppman's Thesis",'1:20',
 ["Here is the thesis in his own words: he will \"portray her not as a mystic but as a serious thinker.\" Note the two contrasts. Against \"ecstatic assertions,\" he offers \"careful sequences of ideas and images.\" Against \"abandonment to excess,\" he offers \"thoughtful production of, and reaction to, extreme states of being.\"",
  "So the claim is strong: the movement of thinking itself is the real subject of her poems. His stated goal -- and I'd underline this -- is to show \"how writing poetry helped her think.\" Keep one question alive as we go: can thought and feeling actually be separated? I don't think they can -- and I don't think his own evidence lets him."],
 ["This is THE thesis sentence -- read it verbatim.",
  "Plant your counter-question here (thought/feeling inseparable).",
  "Color: the thesis quote is Deppman (blue)."])

slide('6','The Statistical Evidence','1:30',
 ["Deppman's first move is admirably concrete: he counts. Using the Rosenbaum Concordance, on the feeling side -- feel 39, felt 35, feels 16, feeling 8; body only 10. On the thinking side, far larger -- thought 69, think 43, and \"know\" 230 times. \"Know\" is effectively the fourth most common verb in her whole corpus. \"Mind\" 79, \"brain\" 26.",
  "The contrast is hard to ignore, and Deppman concludes her poetry is \"much more about thought than feeling.\" This is the strongest, most falsifiable part of the essay. But -- and this matters -- he himself acknowledges the statistics are \"partial and decontextualized.\" And he's right: word-counts show what she talks about, not her attitude, and certainly not that thought is opposed to feeling."],
 ["Emphasize 230 vs. 39 -- the striking number.",
  "The 'partial and decontextualized' caveat is a seed for Slide 16.",
  "Numbers themselves are neutral (black); Deppman's claim is blue."])

slide('7','The Kaleidoscope of Thought','1:20',
 ["Having shown thought pervades the poems, Deppman stresses it is a \"consistent as well as kaleidoscopic\" topic -- she treats it from many angles. Celebratory: \"Best Things dwell out of Sight ... Our Thought.\" Cautionary: \"If wrecked upon the Shoal of Thought.\" Analytic: \"The Brain is wider than the Sky.\" Wild: \"The Brain, within its Groove ... But let a Splinter swerve.\" And sufficient for happiness: \"The revery alone will do, if bees are few.\"",
  "The point: thought is not a byproduct of her poems -- it is a deliberate, many-sided subject."],
 ["Read one or two poem fragments aloud for texture.",
  "The phrase 'kaleidoscopic' is Deppman's (blue); poems are Dickinson (green)."])

slide('8','Postmodern Dickinson?','1:30',
 ["Deppman then places Dickinson on a map of theory. Wolff calls her an \"artist of the age of transition,\" freeing language \"from the tyranny of His definitions\" -- God's authority. Porter describes her mind as \"explosive with signifying power but disinherited from transcendent knowledge\": enormous energy, no stable God to anchor it. He invokes Lyotard's postmodern -- \"incredulity toward metanarratives\" -- and Derrida's \"bricoleuse,\" who mixes religious, literary, and scientific vocabularies.",
  "The root of it all is a specific tension: between the Lockean empiricism of her schoolbooks and the Kantian, Transcendentalist idea that the mind can reach the supersensible. Dickinson stands in that gap -- and it's the Kantian side that becomes the engine of the essay."],
 ["Move briskly -- this is a list of critics; don't linger.",
  "All these are quoted from Deppman 86 (note the footer).",
  "Bridge to next slide: 'and here is that Kantian engine.'"])

slide('9','The Kantian Sublime','1:40',
 ["Here is the engine of the whole argument -- the Kantian sublime, the very scene Lyotard turns into the postmodern condition. Four steps. One: reason conceives something conceivable but unpresentable -- infinity, death. Two: reason demands an adequate image. Three: imagination tries -- and fails; the thing is too big to picture. Four: the mind keeps trying, and from this straining the feeling of the sublime is born. Lyotard reframes it as the artist's task: to \"invent allusions to the conceivable which cannot be presented.\"",
  "Notice the word feeling in step four -- even in the theory, the sublime is an experience. And here is the key acknowledgment: Deppman admits Dickinson \"did not read Kant.\" His claim is a shared attitude, not influence. Hold that question: if she never read Kant, is the sublime something he finds, or something he brings?"],
 ["Draw or trace the try -> fail -> repeat loop.",
  "Stress 'did not read Kant' -- it returns in Slide 16 as 'Kant without Kant.'",
  "The word 'feeling' in step 4 supports your thesis-collapse argument."])

slide('10','The Higginson Letters (Letters with Higginson)','1:30',
 ["Deppman's next evidence is Dickinson's correspondence with Higginson -- her only sustained literary exchange. His claim: she understood writing AS thinking. In 1862 she asks: \"Are you too deeply occupied to say if my Verse is alive?\" -- not pretty, not correct, but alive: is the thought living? And she explains the bind: \"The Mind is so near itself -- it cannot see, distinctly -- and I have none to ask.\"",
  "But note WHY she writes: \"I had a terror ... and so I sing, as the Boy does by the Burying Ground -- because I am afraid.\" Deppman himself calls writing \"thought's psychotherapeutic response to troubling emotion.\" Even as he builds the case for thought, he tells us the thinking exists to manage feeling. And to the very end: \"bereft of Book and Thought.\""],
 ["Highlight the 'therapy' quote -- your key evidence for Slide 16.",
  "All quotes here are Dickinson (green).",
  "Note her frustration when Higginson replies about form, not thought."])

slide('11','Defining the "Try-to-Think" Poem','1:10',
 ["All this converges on Deppman's central contribution: the \"try-to-think\" poem. Its purpose is to force the mind to satisfy reason's unsatisfiable demand for a complete image. Its features: \"the try is usually serious, the goal explicitly stated, ... emphasis squarely on the willful movements of thought.\" These are \"precisely sequenced, if difficult, thought experiments\" -- and they invite the reader to repeat the steps. Examples include \"Of Death I try to think like this\" and \"I think To Live -- may be a Bliss.\"",
  "This is a real critical achievement: it names a genuine, recurring pattern. So let's watch it operate on the poem Deppman treats as its masterpiece."],
 ["This concept is the paper's original contribution -- give it credit.",
  "But note (for Slide 16) the genre is defined FROM the poems it explains."])

slide('12','Close Reading 1: Fr570 and the Dilemma','1:40',
 ["The poem is \"I tried to think a lonelier Thing,\" from 1863. It opens with the speaker trying to name a loneliness worse than any she has seen -- \"Some Polar Expiation,\" \"An Omen in the Bone / Of Death's tremendous nearness\" -- and ends, after plucking at a \"Partition,\" with: \"I almost strove to clasp his Hand, / Such Luxury -- it grew -- / That as Myself -- could pity Him -- / Perhaps he -- pitied me.\"",
  "Deppman poses a sharp dilemma. Is the trying proactive -- a \"virtuoso attempt to conceptualize an extreme human possibility\"? Or reactive -- an attempt \"to knead it, battle it, alter it, realize it, or just survive it through thought\"? He chooses reactive. And that choice is decisive: if the poem is reactive, the pain comes first, and thinking is the response. That is not thought instead of feeling; it's thought because of feeling."],
 ["Read the poem excerpt slowly.",
  "'Deppman chooses reactive' -- circle this; it's your pivot to Slide 16.",
  "Poem = green; the two options + 'reactive' = Deppman (blue)."])

slide('13','Close Reading 2: Tracking the Steps (Fr570)','1:50',
 ["Let's track the sequence, because this is where the reading is most impressive. First, the speaker names the \"Thing\" as two quiddities. \"Some Polar Expiation\" -- expiation plus a pun on polar expedition: radical exile from self, culture, and nature. Then \"An Omen in the Bone / Of Death's tremendous nearness\" -- anticipatory: death felt near in both time and space.",
  "Second, she borrows a \"Duplicate\" -- another spirit \"Of Heavenly Love -- forgot\" -- what Deppman calls \"the smallest possible unit of imagined community.\" She is so alone she must invent a fellow sufferer. Third, the crucial ambiguity: \"Within the Clutch of Thought\" is undecidable -- reachable BY thought, or made ONLY of thought, fabricated? Everything hangs on this. And fourth: \"our Partition\" -- the possessive forms \"a we.\" That tiny word makes a relationship where there was only solitude: both barrier and bridge between the living self and the dead twin."],
 ["This is the heart of the talk -- show theory (Slide 9) operating on text.",
  "Green = Dickinson's words; blue = Deppman's readings ('a we' is blue!).",
  "Slow down on the 'undecidable' point -- it's the poem's hinge."])

slide('14','Close Reading 3: The Paradoxical Close (Fr570)','1:30',
 ["Now the ending, strange and moving. The speaker and her invented duplicate are two God-forsaken souls in \"Opposing Cells\" -- Deppman calls it \"a chilling scene reminiscent of Beckett's Godot.\" Then Deppman does something bold: he inserts an elided phrase, reading it as \"Such Luxury -- it grew [-- to think].\" On his reading, the strange comfort comes from the experimental force of thought itself.",
  "But listen to how he describes it: \"a fragile state and a momentary victory: how long can meditating on one's dead duplicate continue to console?\" And here is my point: the victory is fragile precisely because it is emotional. A proof doesn't decay; a feeling of comfort does. The instability of the ending is the instability of a mood -- so the poem that supposedly shows thought's triumph ends by showing thought's dependence on a passing emotional state."],
 ["Note that '[to think]' is INSERTED -- not in the original (your critique word).",
  "The 'fragile / momentary' quote is Deppman's own -- he undermines himself.",
  "This is the bridge into your position: fragile = emotional."])

slide('15','Critical Assessment: Strengths','1:15',
 ["Before I push back, let me give the essay its due. Four real strengths. First, methodological rigor: he grounds a big claim in concordance data, not impression -- a falsifiable, checkable move, rare in criticism. Second, genuine integration: the letters function as evidence of a poetics, not decorative biography. Third, and most durable, the \"try-to-think poem\" is a generative concept -- we can apply it to poems he never discusses. Fourth, he reframes Dickinson's difficulty: where others saw opacity as failure or excess, he lets us see it as the trace of a mind at work.",
  "So this is a strong, serious essay -- which is exactly why it's worth pressing on its central claim."],
 ["Be genuinely fair here -- it earns credibility for your critique.",
  "Keep this slide calm/black; save the red for Slide 16.",
  "End with the turn: 'which is why it's worth pressing.'"])

slide('16','Critical Assessment: My Position','1:50',
 ["Here is my position, plainly: the thesis is self-undermining -- and that is the most interesting thing about it. Deppman chooses thought over feeling. Yet his own reading of Fr570 runs on affect: he calls the scene \"chilling,\" speaks of \"sickening loneliness,\" and defines writing as \"thought's psychotherapeutic response to troubling emotion.\" Every one of those is an affective term.",
  "So the contradiction: if the \"try\" matters only because the loneliness is unbearable -- and he insists the poem is reactive -- then thought and feeling cannot be pulled apart. The binary he builds his essay on collapses under his own evidence. Thus the real achievement is the opposite of the stated one: thinking is an emotional act. I don't think this makes the essay a failure -- it makes it truer than its thesis.",
  "Three quick pressure points for discussion: \"Kant without Kant\" -- is the sublime a lens he finds or imposes? The circularity of the genre -- defined from the poems it then explains. And Muldoon's Civil War reading of the poem, which Deppman rejects."],
 ["This is the climax -- commit fully to the stance.",
  "The affect words are Deppman's own (blue) -- that's the proof.",
  "Deliver 'thinking is an emotional act' slowly; it's your core sentence.",
  "Invite disagreement openly."])

slide('17','Conclusion & Discussion Questions','1:15',
 ["Let me draw it together. Deppman ends honestly: we never know whether Dickinson succeeded in thinking what she tried to think. What we know is that these are poems in which she \"tried to help or save herself by representing her own efforts to help or save herself.\" To read them is to risk \"experiencing a loneliness we cannot sound.\"",
  "And that returns us to Kierkegaard -- the more consciousness, the more despair. Thought, in Dickinson, is never pure consolation; it is consolation AND risk at once. Which is why I've argued you cannot cleanly separate her thinking from her feeling. Four questions for us: Does the thought/feeling binary survive Deppman's own close reading? Is the Kantian sublime valid for a poet who never read Kant? Is \"try-to-think\" a discovered genre or a critic's construct? And -- does Kierkegaard's equation of consciousness with despair hold for Dickinson's poetry?"],
 ["Return to Kierkegaard -- name the bookend explicitly.",
  "End on the questions, not a summary -- hand the floor over.",
  "Q4 was changed to Kierkegaard (not Muldoon) to close the circle."])

slide('18','"I dwell in Possibility --"','0:40',
 ["I'll end where Dickinson might want us to. Her line: \"I dwell in Possibility.\" I've argued that Deppman sets out to prove her a thinker rather than a feeler, and that his own reading dissolves that distinction -- because in Dickinson, to think the unthinkable is to feel it. But that dissolution doesn't reduce her; it opens her. If her poems are experiments we're invited to try rather than conclusions we're handed, then reading her is never finished -- it's a space we dwell in. That is why she dwells in Possibility, and why we are still trying to think with Emily Dickinson. Thank you."],
 ["Slow, warm close. Let the final line land.",
  "Then open Q&A."])

# closing timing table page
w.newpage()
w.line('Timing Summary',16,'/F2',gap=10,color=ACCENT)
w.rule()
rows=[('1 Title','0:45'),('2 Contents','0:50'),('3 Epigraphs','1:20'),
('4 Critical Debate','1:30'),('5 Thesis','1:20'),('6 Statistical Evidence','1:30'),
('7 Kaleidoscope','1:20'),('8 Postmodern','1:30'),('9 Kantian Sublime','1:40'),
('10 Higginson Letters','1:30'),('11 Try-to-Think','1:10'),('12 Close Reading 1','1:40'),
('13 Close Reading 2','1:50'),('14 Close Reading 3','1:30'),('15 Strengths','1:15'),
('16 My Position','1:50'),('17 Conclusion','1:15'),('18 Possibility','0:40')]
for name,t in rows:
    w.ensure(16)
    w.s.append('BT /F1 12 Tf %d %.1f Td (%s) Tj ET'%(MARGIN,w.y,esc(name)))
    w.s.append('BT /F1 12 Tf %d %.1f Td (%s) Tj ET'%(PAGE_W-MARGIN-40,w.y,esc(t)))
    w.y-=16
w.gap(6); w.rule()
w.line('Total: approximately 25 minutes 35 seconds (Q&A separate).',12,'/F2',gap=8)
w.gap(6)
w.line('If you run short: read the full Fr570 poem aloud (Slide 12, +45s); read the full L10 death-letter passage (+30s); pause for hands after each discussion question (+60s).',11,'/F1',gap=5)
w.line('If you run long: compress the critics on Slide 8; shorten the four-step sublime on Slide 9 to two; cut the three pressure points on Slide 16 to one.',11,'/F1',gap=5)

w.finish()
pdf.build('/projects/sandbox/dickinson_presentation_script.pdf')
print('Wrote dickinson_presentation_script.pdf')
