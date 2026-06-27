# Street Typer

> A two-player typing fight where the damage you deal equals the bits you transmit, built to test one claim: for a practiced typist, random letters on a keyboard move more information per second than speech or any other channel we measured.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
&nbsp;![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB.svg?logo=python&logoColor=white)
&nbsp;![Dependencies: none](https://img.shields.io/badge/dependencies-none%20(stdlib)-brightgreen.svg)
&nbsp;![Players: 2](https://img.shields.io/badge/players-2-orange.svg)
&nbsp;![Objective: max bits/sec](https://img.shields.io/badge/objective-max%20bits%E2%81%84sec-8a2be2.svg)

You type a stream of random letters. Every clean four-letter block lands an attack, and its damage equals the bits you just transmitted. Your opponent's health bar is sized so that only a sustained 20 bits per second can drain it inside a 60-second round, so the player with the higher information rate wins.

Underneath the fighting game is a bit-rate meter. The rest of this document is about that meter: the quantity it measures, why typing random letters maximizes that quantity for the people who will play it, the other input methods we built and dropped, and the design choices behind the measurement.

## The objective

Every input method gets one score: the information transfer rate it achieves.

```
B = log2(N − 1) · max(Sc − Si, 0) / t          [bits / second]
```

`N` is the alphabet size; `Sc` and `Si` are the counts of correct and incorrect selections; `t` is elapsed seconds. A selection drawn uniformly from `N` options carries up to `log2 N` bits. The conservative `N − 1` and the `max(·, 0)` floor treat an error as forfeiting a selection's worth of credit rather than refunding it.

The formula factors into the only three quantities a player can change:

```
B = log2(N − 1) · R · (2a − 1) ,   R = (Sc + Si) / t ,   a = Sc / (Sc + Si)
```

- `log2(N − 1)`, the bits per selection, is fixed by the alphabet and grows only with the log of `N`, so a wider alphabet pays off slowly.
- `R`, the selections per second, is fixed by how fast the human effector can act.
- `2a − 1`, the share of information that survives the channel, is doubly sensitive: an error both fails to score and subtracts, so accuracy below about 0.9 hurts quickly.

To maximize `B` you have to push all three at once, and they trade against each other. The best modality is the one that happens to sit high on all three for the specific person playing.

## The bottleneck is output, not input

A round is a sequence of selections the player produces, so the binding constraint is output bandwidth. Reading the next target costs almost nothing: vision is the fastest channel into a person, and recognizing a symbol already on the screen is close to instant. So the game shows the targets plainly, reading never gates the loop, and the player's whole budget goes into output. That leaves one question: which output channel maximizes `B`?

## Speech: high bandwidth, low yield

Speech is the highest-bandwidth human output in ordinary use, about 39 bits per second and remarkably steady across seventeen languages (Coupé et al., 2019). It looks like the obvious winner, but it loses here for a reason that is itself information-theoretic.

That 39 bits per second is entropy *given context*. Most of it is predictable from the preceding words and is carried cheaply by the listener's language model across multi-syllable chunks. Our source is i.i.d. uniform, so by construction there is no context to predict from. Take the language model away and two limits bind:

1. Production rate. Reading random tokens aloud, a speaker sustains about 2 to 3 distinct utterances per second, not the 5 to 6 syllables per second of connected speech.
2. Recognition. The recognizer is a noisy channel with its own speed-accuracy tradeoff. We built several: free-transcription digits, vowels, a forced-choice recognizer over a swappable pool, and a continuous LocalAgreement streaming decoder on a fine-tuned small ASR model. On fast, accented, i.i.d. tokens, exact-match accuracy fell to 0.70 to 0.86, and the smallest models dropped into repeat-loops on monotonic input. Even 0.85 accuracy pulls the `(2a − 1)` multiplier down to 0.70.

End to end we measured about 5 bits per second, with an analyzed ceiling near 8. We also pushed on the alphabet axis directly and checked the estimates adversarially:

| source (i.i.d.)            | effective N | bits/sel | sel/s | accuracy | **B (b/s)** |
|----------------------------|:--------:|:--------:|:-----:|:--------:|:-----------:|
| spoken digits 0-9          |    10    |   3.17   |  2.2  |   0.82   |    ~4.5     |
| spoken letter-names        |   ~15\*  |   3.81   |  2.2  |   0.70   |    ~3.3     |
| NATO phonetic words        |   ~24    |   4.52   |  1.0  |   0.78   |    ~2.5     |
| curated monosyllables      |    30    |   4.86   |  1.7  |   0.82   |    ~5.3     |
| **keyboard letters**       |  **26**  | **4.64** | **3-6** |**≈0.97**| **~13-26** |

\*Raw letter-names number 26, but the "E-set" (B, C, D, E, G, P, T, V, Z) collapses into one acoustic class, so the *distinguishable* alphabet is about 15 and exact-match accuracy caps near 0.70.

Every spoken option lands around 4 to 6 bits per second because the three factors trade off against each other: a larger, more distinct vocabulary raises `log2(N − 1)` but lowers the rate (longer words) and the accuracy (more confusable tokens, more hesitation). The product stays flat, and it sits well below typing.

## Why typing wins

The people who will play this are professional software engineers, and for them the keyboard is an overlearned motor program built from years of daily use. That overlearning pays off in all three factors at once.

Accuracy comes from an exact channel. A keypress *is* the symbol; nothing has to recognize it. The full `log2 N` bits per keystroke survive, and `2a − 1` is set by the fingers (around 0.95 to 1.0), not by what a model can decode. This is the largest single gap between typing and speech.

Bits per selection stay cheap because there is no Hick-Hyman tax. Choice reaction time grows with the information in the choice, `RT = a + b·log2 N` (Hick 1952; Hyman 1953), but only for unfamiliar choices. Overlearning drives the slope `b` toward zero: a touch-typist does not deliberate among 26 keys, because the path from seeing a letter to pressing it is automatic. So `N = 26` (`log2 25 = 4.64` bits per selection) costs almost no extra time, where an unpracticed mapping would pay in proportion to `log2 N`.

Rate comes from the same automaticity. On random letters, which deny typists the word-level motor programs and anticipation that make prose fast, fluent typists still hold about 3 to 6 keystrokes per second, with the binding limit being finger transport time rather than any decision cost. That transport time is governed by Fitts's law (Fitts 1954), which touch-typing keeps small by anchoring on the home row.

Multiply it out: `4.64 bits/sel × 3-6 /s × ≈0.95 ≈ 13-26 bits/second`, comfortably past the 8 bits per second speech ceiling. A casual but accurate typist already measures 10 to 15; a fast one runs well above 25. Reading keeps up easily, since the eyes pull in the next letters through the fastest input channel a person has.

## Design choices behind the measurement

- A maximal `N`. All 26 letters, each fully distinguishable, so `log2(N − 1)` reflects bits the channel carries rather than an inflated count. We do not count acoustically identical tokens as separate symbols, which would claim bits that never crossed the channel.
- A lossless channel. Typing removes the recognizer, fixes accuracy near 1.0, and recovers the full per-selection entropy that a speech recognizer erodes.
- An i.i.d. uniform source. Maximum entropy for a fixed `N`, with no language model or patterns inflating the score.
- Four-letter chunks. Letters are read and struck in groups of four, which matches how typists buffer and the limits of motor chunking (Miller 1956). Chunking spreads the fixed per-action overhead and sets the attack cadence.
- Competition, which raises both rate and accuracy for a fixed player. The next section explains why.

## Why wrap it in a fight

The fighting game controls the two factors a player can squander, rate and accuracy, and it turns the metric into the mechanic.

Damage is bits. A clean four-letter block deals `log2 25 × (correct − wrong)` damage, and HP is `1200 = 20 b/s × 60 s`, so only a round near 20 bits per second can empty a bar. The objective and the win condition are the same function, so there is no way to win except by maximizing `B`.

Competition raises `B` for the same pair of hands. Performance climbs with arousal up to a point (Yerkes-Dodson 1908), and a live opponent with a draining health bar supplies a measured stake that pushes attention toward its peak and holds it there. A clear goal, instant feedback, and a challenge matched to skill are also the conditions for flow (Csikszentmihalyi 1990). Sustained attention is what lifts `R` and suppresses the slips that cost the `(2a − 1)` term. The same hands produce a higher `B` under pressure than in a solo trial, so the competition directly serves the objective.

## How it works

- It takes two players on two separate devices, each with a physical keyboard (one player per device, because a browser can't tell two keyboards on one machine apart). Both open the same page, each presses Ready, and only then does the 60-second round begin. A single player waits in the lobby.
- N = 26 letters, drawn i.i.d. uniform with replacement. No language model, no patterns.
- Each completed four-letter block is an attack; damage is `log2(25) × (correct − wrong)`.
- The server is the authoritative referee for HP, score, and winner. Browsers send keystroke results and draw the fight. A round runs 60 seconds; the first to 0 HP wins, otherwise the higher HP at the buzzer takes it.
- The end screen reports each player's `B`, `Sc`, and `Si`, so the measurement is visible.
- No dependencies. The server is pure Python standard library and the client is a single HTML page. Transport is SSE plus POST, and a reconnect reclaims the same player slot by token.

## Run it

Two players, one shared URL. Deploy it as a web service (Render's free tier works) and both players open the same link: the first becomes Player 1, the second Player 2. The round begins only when both players are on the page and each presses Ready. The start command is `python fight_server.py --cloud`. Full steps are in **[DEPLOY.md](DEPLOY.md)**. To play on a local network instead, run `python fight_server.py` (or use the double-click launchers) and the second machine discovers the first automatically. Any device with a physical keyboard works, including a tablet with an attached keyboard (Bluetooth, USB, or a folio keyboard).

## Custom fighters

Each character is a folder of transparent frame images plus a `manifest.json`, with the states `intro`, `idle`, `attack1` through `attack4`, `hurt`, `win`, and `lose`. Drop in your own filmed, step-printed frames and they appear with no code change. The filming guide, the processing pipeline, and the acceptance criteria are in **[PROCESSING.md](PROCESSING.md)**.

## References

- Shannon, C. E. (1948). *A Mathematical Theory of Communication.* Bell System Technical Journal.
- Hick, W. E. (1952). *On the rate of gain of information.* Quarterly Journal of Experimental Psychology.
- Hyman, R. (1953). *Stimulus information as a determinant of reaction time.* J. Experimental Psychology.
- Fitts, P. M. (1954). *The information capacity of the human motor system in controlling the amplitude of movement.* J. Experimental Psychology.
- Miller, G. A. (1956). *The magical number seven, plus or minus two.* Psychological Review.
- Yerkes, R. M., & Dodson, J. D. (1908). *The relation of strength of stimulus to rapidity of habit-formation.* J. Comparative Neurology and Psychology.
- Csikszentmihalyi, M. (1990). *Flow: The Psychology of Optimal Experience.*
- Coupé, C., Oh, Y., Dediu, D., & Pellegrino, F. (2019). *Different languages, similar encoding efficiency: comparable information rates across the human communicative niche.* Science Advances 5(9).

MIT licensed. See [LICENSE](LICENSE).
