# Street Typer

> **A two-player typing fight whose damage is the information you transmit — and the case, in math and measurement, for why overlearned i.i.d. keyboard typing beats speech and every other modality at raw bit rate.**

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
&nbsp;![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB.svg?logo=python&logoColor=white)
&nbsp;![Dependencies: none](https://img.shields.io/badge/dependencies-none%20(stdlib)-brightgreen.svg)
&nbsp;![Players: 2](https://img.shields.io/badge/players-2-orange.svg)
&nbsp;![Objective: max bits/sec](https://img.shields.io/badge/objective-max%20bits%E2%81%84sec-8a2be2.svg)

A two-player typing duel in which the win condition is, literally, your information transfer rate.
You type a stream of random letters; every clean four-letter block lands an attack whose damage equals
the bits you just transmitted. The opponent's health bar is sized so that only a sustained **~20
bit/second** performance can empty it inside a 60-second round. Out-type your rival and you win.

The game is a measurement instrument wearing a fighting game. This document is about the instrument:
the quantity it optimizes, why typing random letters on a keyboard maximizes that quantity for the
people playing it, the modalities we built and discarded along the way, and the techniques that buy
bits.

## The objective

One number scores every input method — the achieved information transfer rate:

```
B = log2(N − 1) · max(Sc − Si, 0) / t          [bits / second]
```

`N` is the alphabet size, `Sc` and `Si` the number of correct and incorrect selections, `t` the
elapsed seconds. A selection drawn uniformly from `N` options carries up to `log2 N` bits; the
conservative `N − 1` and the `max(·, 0)` floor model an error as forfeiting a selection's worth of
credit rather than refunding it.

It factors into the only three quantities a player can move:

```
B = log2(N − 1) · R · (2a − 1) ,   R = (Sc + Si) / t ,   a = Sc / (Sc + Si)
```

- **`log2(N − 1)` — bits per selection** (complexity). Fixed by the alphabet; grows *sublinearly* in `N`.
- **`R` — selections per second** (speed). Fixed by the human effector.
- **`2a − 1` — information that survives the channel** (accuracy). Doubly sensitive: an error both
  fails to score *and* subtracts, so accuracy under ~0.9 is brutal.

Maximizing `B` is the joint maximization of these three. They trade against one another, and the right
modality is the one that is simultaneously high on all three *for the person playing*.

## Input is cheap; output is the bottleneck

A round is a sequence of selections the human emits — an output-bandwidth problem. The input side,
reading the next target, is nearly free: vision is the highest-throughput channel *into* a person, and
recognizing one already-displayed symbol is effectively instantaneous. So the targets are shown
plainly, reading never gates the loop, and the player's whole budget goes to output. The only question
is which output channel maximizes `B`.

## Speech: the fast modality that loses

Speech is the highest-bandwidth human output in ordinary use — about **39 bits/second**, near-constant
across seventeen languages (Coupé et al., 2019). It is the obvious answer, and it is the wrong one
here, for a reason that is itself information-theoretic.

That 39 bits/second is entropy *given context*. Most of it is predictable from preceding words and is
carried cheaply by the listener's language model over multi-syllable units. Our source is **i.i.d.
uniform** — there is, by construction, no context to predict from. Remove the language model and two
limits bind:

1. **Production rate.** Reading random tokens aloud, a speaker sustains ~2–3 distinct utterances per
   second, not the 5–6 syllables/second of connected speech.
2. **Recognition.** The recognizer is a noisy channel with its own speed–accuracy tradeoff. We built
   several — free-transcription digits, vowels, a forced-choice recognizer over a swappable pool, and a
   continuous LocalAgreement streaming decoder over a fine-tuned small SOTA ASR model — and measured
   accuracy on fast, accented, i.i.d. tokens falling to **0.70–0.86**, with small models dropping into
   repeat-loops on monotonic input. Through the `(2a − 1)` term, 0.85 accuracy alone cuts the
   multiplier to 0.70.

End to end we measured **~5 bits/second**, with an analyzed ceiling near 8. We also worked the alphabet
axis directly and adversarially checked the estimates:

| source (i.i.d.)            | honest N | bits/sel | sel/s | accuracy | **B (b/s)** |
|----------------------------|:--------:|:--------:|:-----:|:--------:|:-----------:|
| spoken digits 0–9          |    10    |   3.17   |  2.2  |   0.82   |    ~4.5     |
| spoken letter-names        |   ~15\*  |   3.81   |  2.2  |   0.70   |    ~3.3     |
| NATO phonetic words        |   ~24    |   4.52   |  1.0  |   0.78   |    ~2.5     |
| curated monosyllables      |    30    |   4.86   |  1.7  |   0.82   |    ~5.3     |
| **keyboard letters**       |  **26**  | **4.64** | **3–6** |**≈0.97**| **~13–26** |

\*Raw letter-names are 26, but the "E-set" — B C D E G P T V Z — collapses to one acoustic class, so the
*distinguishable* alphabet is ~15 and exact-match accuracy caps near 0.70.

Every spoken option saturates around 4–6 bits/second because the three factors trade off: a larger,
more distinct vocabulary raises `log2(N − 1)` but lowers the rate (longer words) and the accuracy (more
confusable tokens, more hesitation). The product is flat — and it sits well below typing.

## Typing: overlearned, exact, fast, wide

The intended players are professional software engineers, for whom the keyboard is an **overlearned
motor program** built over years of daily use. Overlearning pays off in all three factors at once.

**Exact channel → accuracy.** A keypress *is* the symbol; no recognizer stands between intent and
selection. The full `log2 N` bits per keystroke survive, and `2a − 1` is set by the fingers (≈0.95–1.0),
not by what a model can decode.

**No Hick–Hyman tax → bits per selection come cheap.** Choice reaction time grows with the information
of the choice, `RT = a + b·log2 N` (Hick 1952; Hyman 1953) — for *novel* choices. Overlearning drives
the slope `b` toward zero: a touch-typist does not deliberate among 26 keys, the stimulus→finger map is
automatic. So `N = 26` (`log2 25 = 4.64` bits/selection) costs almost no extra time per selection, where
an unpracticed mapping would pay in proportion to `log2 N`.

**Automaticity → rate.** On *random* letters — which resist the word-level motor programs and
anticipation that make prose typing fast — fluent typists still sustain ~3–6 keystrokes/second, and the
binding limit is finger transport time governed by Fitts's law (Fitts 1954), which touch-typing
minimizes by keeping movement amplitudes small (home-row anchoring). The ceiling is muscle, not
cognition.

The product — `4.64 bits/sel × 3–6 /s × ≈0.95 ≈ 13–26 bits/second` — clears the ~8 b/s speech ceiling
comfortably. A casual but accurate typist already lands 10–15 b/s (measured); a fast one, well past 25.
Reading closes the loop: the eyes ingest the next letters through the fastest input channel a human has,
so the hands are never starved.

## Techniques that buy bits

- **Honest, maximal `N`.** 26 letters, every one exactly distinguishable, so `log2(N − 1)` is real bits
  rather than inflated count. (We refuse the trick of counting acoustically identical tokens as separate
  symbols — it would claim bits the channel never carried.)
- **A lossless channel.** Typing removes the recognizer entirely, fixing `a ≈ 1` and recovering the full
  per-selection entropy. This is the single largest win over speech.
- **An i.i.d. uniform source.** Maximum entropy for a fixed `N`, and an honest measurement: no language
  model, no patterns, no predictive coding inflating the score.
- **Four-letter chunking.** Letters are read and struck in groups of four, matching how typists buffer
  and the limits of motor chunking (Miller 1956). Chunking amortizes the fixed per-action overhead,
  lifting `R`; it also sets the attack cadence.
- **Competition as an attention regulator** (below).

## Why a fight

The wrapper is not decoration. It regulates the two factors a player can blow — rate and accuracy — and
it makes the metric the mechanic.

**Damage equals bits.** A clean four-letter block deals `log2 25 × (correct − wrong)` damage; HP is
`1200 = 20 b/s × 60 s`, so only a ~20 bit/second round empties a bar. The objective function and the win
condition are the same function — you cannot win by doing anything other than maximizing `B`.

**Competition raises `B` for a fixed player.** Performance rises with arousal up to a point
(Yerkes–Dodson 1908); a live opponent and a draining bar supply a calibrated stake that pushes attention
toward its peak and holds it there — a clear goal, immediate feedback, and challenge matched to skill,
the conditions for flow (Csikszentmihalyi 1990). Sustained attention is exactly what lifts `R` and
suppresses the lapses that cost `2a − 1`. The same hands produce a higher `B` under pressure than in a
solo trial — so the entertainment is, directly, an optimization of the objective.

## How it works

- **N = 26 letters**, drawn i.i.d. uniform with replacement — no language model, no patterns.
- Each completed **4-letter block** is an attack; damage `= log2(25) × (correct − wrong)`.
- The **server is the authoritative referee** (HP, score, winner); browsers send keystroke results and
  render the fight. A round is 60 s; first to 0 HP wins, otherwise higher HP at the buzzer.
- The end screen reports each player's `B`, `Sc`, `Si` — the measurement, exposed.
- **No dependencies.** The server is pure Python standard library; the client is one HTML page. Transport
  is SSE + POST; reconnects reclaim the same player slot by token.

## Run it

Two players, one shared URL: deploy as a web service (Render's free tier works) and both open the link —
first is Player 1, second is Player 2. `Start command: python fight_server.py --cloud`. Full steps in
**[DEPLOY.md](DEPLOY.md)**. To play on a local network instead, run `python fight_server.py` (or the
double-click launchers) and the second machine auto-discovers the first.

## Custom fighters

Each character is a folder of transparent frame images plus a `manifest.json` (states `intro, idle,
attack1–4, hurt, win, lose`); drop in your own filmed, step-printed frames and they appear with no code
change. Filming guide, the automated processing pipeline, and the acceptance criteria are in
**[PROCESSING.md](PROCESSING.md)**.

## References

- Shannon, C. E. (1948). *A Mathematical Theory of Communication.* Bell System Technical Journal.
- Hick, W. E. (1952). *On the rate of gain of information.* Quarterly Journal of Experimental Psychology.
- Hyman, R. (1953). *Stimulus information as a determinant of reaction time.* J. Experimental Psychology.
- Fitts, P. M. (1954). *The information capacity of the human motor system in controlling the amplitude
  of movement.* J. Experimental Psychology.
- Miller, G. A. (1956). *The magical number seven, plus or minus two.* Psychological Review.
- Yerkes, R. M., & Dodson, J. D. (1908). *The relation of strength of stimulus to rapidity of
  habit-formation.* J. Comparative Neurology and Psychology.
- Csikszentmihalyi, M. (1990). *Flow: The Psychology of Optimal Experience.*
- Coupé, C., Oh, Y., Dediu, D., & Pellegrino, F. (2019). *Different languages, similar encoding
  efficiency: comparable information rates across the human communicative niche.* Science Advances 5(9).

MIT licensed — see [LICENSE](LICENSE).
