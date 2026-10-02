# PitchVision — Final Presentation Script
**PARC 2026 AI League · Virtual Final Presentation, 10/8/26**

Pace target ~140 words/min → **total ≈ 9:18** (≈ 9:38 if you speak slower, at 135 wpm). The cap is 10:00 (−2 pts per minute over).
Every presenter clears the 2-minute minimum even at a fast 155 wpm (−2 pts per person under).
The same text is in each slide's Notes panel in the .pptx. The demo procedure is in **PitchVision_Demo_Runbook.md**; the notebook is **PitchVision_Live_Demo.ipynb**.

| Order | Presenter | Slides | Time |
|---|---|---|---|
| 1st | Clifford | 1–3 (title, problem, task & question) | ~2:18 |
| 2nd | Phanice | 4–5 (model, experiment) | ~2:14 |
| 3rd | Kevin | 6–7 (results, what did not hold up) | ~2:20 |
| 4th | Brian | 8–10 (**live demo**, direction, close) | ~2:26 |

**Stage cues** (Brian, slide 8): **[START THE RUN]** = switch to the Colab tab and run cell 4. **[BACK TO THE SCREEN]** = run cells 5 and 6. Exact clicks are in the runbook.

**If you are running long in rehearsal, cut these first (in this order):**
1. Brian, slide 8: *"We added that second audience deliberately … brings the next club to us."* (≈ 30 words)
2. Kevin, slide 7: *"It's also why we published the random-guessing baseline …"* (≈ 28 words) — only if Kevin is comfortably above 2:00.
3. Clifford, slide 2: *"Professional clubs pay people to tag every pass by hand. Grassroots clubs go without."* (≈ 15 words) — only if Clifford is comfortably above 2:00.

**Handoff lines** (each speaker ends by naming the next): Clifford → Phanice ("Phanice will take you through the model"), Phanice → Kevin ("Kevin will tell you what came out"), Kevin → Brian ("Brian will show you it running"). Each opens with "Thanks, <previous speaker>."

---

## Slide 1 — Title — **Clifford** — 0:00–0:31

> Good afternoon, judges. We're Team PitchVision. In the next ten minutes: the problem, the question we set out to answer, how we tested it honestly, what we found, and then we'll run it live on a match it has never seen. The one-line version: we built an AI that watches a football match and tells you exactly when each thing happened, so nobody has to sit through ninety minutes to find three moments.

## Slide 2 — The problem — **Clifford** — 0:31–1:22

> Here's the problem in plain terms. A football match lasts ninety minutes. The parts anyone cares about add up to about ninety seconds. Somebody already filmed it, usually on one sideline camera or a parent's phone, but nobody has time to watch it again. A coach wants the dozen moments that decide next Saturday, and finding them means dragging a slider back and forth for an hour. Parents want the clip where their team scored, and what they get is a ninety-minute file, so they watch none of it. Professional clubs pay people to tag every pass by hand. Grassroots clubs go without. The footage already exists. What's missing is any way to find the moments inside it.

## Slide 3 — The task & our question  [rubric 1] — **Clifford** — 1:22–2:18

> So here's the task. The model looks at one frame every second, and for each second answers one question: did something happen right here, and which of twelve things was it — a pass, a shot, a tackle, a throw-in. What comes out is a timestamped list: a table of contents for a football match. That led us to the question we actually studied. How much video either side of a moment should the model look at, in order to place that moment accurately? Our hunch was that a short look keeps the timing sharp, while a long look buries the moment in everything around it — like being asked what happened at one exact second and answering by summarising the whole minute. Phanice will take you through the model.

## Slide 4 — The model  [rubric 2] — **Phanice** — 2:18–3:31

> Thanks Clifford. The model is simpler than people expect. It does four things. It takes one frame a second. It turns that picture into a list of numbers describing what's in it, using a standard image model. Then — and this is the part our experiment changes — it looks at a window of a few seconds either side of the moment it's judging. Finally it scores each of the twelve event types for that second. The red box is the only thing we vary in the entire study: how wide that window is. What's striking is the size. The whole model is about two hundred thousand numbers — a single phone photo has more pixels than our model has parameters. One training run takes about eight seconds on a free Colab GPU, which is why we could afford fifteen of them. And it scores a match roughly twenty thousand times faster than real time. That matters: this has to run cheaply on ordinary hardware, or grassroots clubs can't use it.

## Slide 5 — The experiment  [rubric 3] — **Phanice** — 3:31–4:32

> Now the experiment. Good experiments change one thing and hold everything else still. We compared three settings: a short seven-second look, a fifteen-second baseline, and a long thirty-one-second look. Same footage, same settings, same training. Only the window changed. The data is real Championship broadcast matches, professionally labelled: four to learn from, one to check progress, and two we deliberately did not open until the very end. Three things kept us honest. Every setting was trained five separate times from different random starting points, so a result only counts if it holds up five times out of five. We compared every number against what pure random guessing scores on the same data, to be sure we were measuring skill. And those last two matches were opened exactly once, at the end, with no tuning afterwards. Kevin will tell you what came out.

## Slide 6 — What we found  [rubric 4] — **Kevin** — 4:32–5:38

> Thanks Phanice. These are the scores on the two matches the model had never seen. Higher is better. Teal is one match, lighter is the other, and the pattern is the same in both: seven seconds is clearly ahead, and it drops as the window gets longer. Three things. First, this held five times out of five on both unseen matches — not one lucky run. Second, and this is the number I'd point you to: pure guesswork scores about 0.23 here, and only the seven-second bars are meaningfully above it. The fifteen and thirty-one second models land level with random guessing on footage they've never seen. So the window isn't a minor tuning detail — it's the difference between a model that works and one that doesn't. Third, the advantage was biggest on the strictest test, pinning the exact second, which is what the product needs. So the answer is: less is more.

## Slide 7 — What did not hold up — **Kevin** — 5:38–6:52

> Now what didn't work, because that matters as much. Three of our smaller claims did not survive that second unseen match. We expected the longest window to be clearly worse than baseline — true on one match, a tie on the other. We expected our advantage to be biggest on the strictest timing test — true on two matches, flat on the third. And we thought shorter windows would time events more precisely, but that reversed on the third match, so we dropped the claim from the report. We also caught a flaw in our own first scoring method: it was generous enough that even random guessing looked respectable. We fixed it and report both versions. None of this touches our main finding, which held everywhere. But we'd rather show you the cracks than have you find them. It's also why we published the random-guessing baseline next to every single number in the report, so anyone reading it can see exactly how much of our score is skill. Brian will show you it running.

## Slide 8 — LIVE DEMO — **Brian** — 6:52–8:28

> Thanks Kevin. Everything so far is research — let me show you what actually comes out the other end. I'm starting it now on a match the model was never trained on — just the first ten minutes, to keep us on time — and it will process while I talk. It's the same model as in the report, and nothing has been tuned for this clip. [START THE RUN]
>
> While that works, here's why it matters commercially. One upload, and two very different people get something they can't get today. A coach or analyst gets a searchable timeline and simple statistics without rewatching ninety minutes to find three moments. Players, parents and fans get an automatic highlight reel and something shareable. We added that second audience deliberately: clubs already have tools, even expensive ones, but fans have nothing at all — and every clip a parent shares brings the next club to us.
>
> [BACK TO THE SCREEN] And here it is. A timeline: each line is something the model spotted, with the moment it happened. The bar is the model's own score, and as the earlier slides showed, it isn't perfect. But instead of a ninety-minute file, you get a list you can jump around in. Let me filter it down to just the crosses — and there they are, each with a time you can go straight to.

## Slide 9 — Where this goes — **Brian** — 8:28–8:59

> So that's the direction: one upload, two audiences, both currently getting nothing. As for what's next, three things. Our own trend line says we should try windows even shorter than seven seconds. We need more matches and more leagues to settle the questions our three couldn't. And critically, our footage is broadcast television, while the real goal is a phone on a tripod at a local ground. That's the gap we close next.

## Slide 10 — Thank you — **Brian** — 8:59–9:18

> So, to close: we asked how much context an action-spotting model needs, tested it across three matches and five repeats, and found that less context gives better timing on footage it had never seen. Thank you — we're happy to take your questions.

---

## Q&A prep (5 minutes, judged separately)

1. **"Your model barely beats random guessing — is it actually working?"** *(Kevin)* At the strictest timing test it beats chance by a wide margin; it is the loose-tolerance averages that compress toward chance, because this data has an event every three seconds. We print the chance baseline beside every number so that is visible.
2. **"Only three matches — how do you know it generalises?"** *(Phanice)* We don't claim general robustness. We claim the ordering held on two matches the model was never trained on, five runs each. More fixtures is our stated next step.
3. **"Why such a small model?"** *(Phanice)* Deliberate. It has to run on cheap hardware for grassroots clubs, and it let us run fifteen full experiments instead of one.
4. **"What happens on a phone camera instead of broadcast TV?"** *(Clifford)* Untested, and we say so in the report. Collecting real single-camera footage is the next thing we do.
5. **"How would you make money?"** *(Clifford)* Still open. Likely free for fans and grassroots to drive adoption, paid tiers for clubs that want the full analyst dashboard.
6. **"What would you do with three more months?"** *(Brian)* Shorter windows, more leagues, and a real single-camera pilot with one club.
7. **"Are those crosses actually right?"** *(Brian)* Run notebook cell 7. It compares the list with the professional annotations and prints how many match. Read out whatever it says, plainly. Then: "That's why we measured on labelled matches rather than trusting the score."
8. **"Why only ten minutes?"** *(Brian)* To keep the demo inside our time. The pipeline is identical for a full match; it just takes proportionally longer.
9. **"Is this a finished product?"** *(Brian)* No. The research result is finished and reproducible; the app around it is the direction we're building toward.

**If a question lands outside your section,** try it first using the notes above, then hand off — "Kevin can give you the detail on that."
