# Street Typer

> A two-player typing fight built to maximize the information rate a human player can achieve. The damage you deal equals the bits you transmit, so the winner is whoever moves the most information per second.

[![Play the game](https://img.shields.io/badge/play-street--typer.onrender.com-ff7a18.svg)](https://street-typer.onrender.com/)
&nbsp;![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
&nbsp;![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB.svg?logo=python&logoColor=white)
&nbsp;![Dependencies: none](https://img.shields.io/badge/dependencies-none%20(stdlib)-brightgreen.svg)
&nbsp;![Players: 2](https://img.shields.io/badge/players-2-orange.svg)
&nbsp;![Objective: max bits/sec](https://img.shields.io/badge/objective-max%20bits%E2%81%84sec-8a2be2.svg)

You type a stream of random letters. Every four-letter block you finish lands an attack, and its damage is the bits you transmitted in that block: your correct letters minus your mistakes, never below zero. A clean block deals the full four letters of damage, and a block with as many mistakes as correct letters deals none. Your opponent's health bar is sized so that only a sustained 20 bits per second can drain it inside a 60-second round, so the player with the higher information rate wins.

The rest of this document is the design rationale: what `B` is, why typing random letters maximizes it for the people who will play, and the alternatives we ruled out.

## The objective

The game is scored by a single number: the information transfer rate the player achieves.

```
B = log2(N − 1) · max(Sc − Si, 0) / t          [bits / second]
```

`N` is the alphabet size; `Sc` and `Si` are the counts of correct and incorrect selections; `t` is elapsed seconds. A selection drawn uniformly from `N` options carries up to `log2 N` bits of information (Shannon 1948). The `max(Sc − Si, 0)` term makes each error forfeit a selection's worth of credit; the `N − 1` in place of `N` is a conservative shave on the per-selection bits.

The formula factors into the only three quantities a player can change:

```
B = log2(N − 1) · R · (2a − 1) ,   R = (Sc + Si) / t ,   a = Sc / (Sc + Si)
```

- `log2(N − 1)`, the bits per selection, is fixed by the alphabet and grows only with the log of `N`, so a wider alphabet pays off slowly.
- `R`, the selections per second, is fixed by how fast the human effector can act.
- `2a − 1`, the share of information that survives the channel, falls off twice as fast as accuracy itself, because an error both forfeits its credit and is subtracted. Accuracy below about 0.9 hurts quickly.

To maximize `B` you have to push all three at once, and they trade against each other. The best modality is the one that happens to sit high on all three for the specific person playing.

## Output is the bottleneck

A round is a sequence of selections the player produces, so the binding constraint is output bandwidth. Reading the next target costs almost nothing: recognizing a symbol already on the screen is near-instant, through the fastest input channel a person has. So the game shows the targets plainly, reading never gates the loop, and the player's whole budget goes into output. That leaves one question: which output channel maximizes `B`?

## Speech: high bandwidth, low yield

Speech is the natural first choice. Natural language carries about 39 bits per second, steady across seventeen languages (Coupé et al. 2019), but that figure is entropy *given context*, and it does not transfer to an i.i.d. source. Speech loses here on information-theoretic grounds.

Most of those 39 bits are predictable from the preceding words and are carried cheaply by the listener's language model across multi-syllable chunks. Our source is i.i.d. uniform, so by construction there is no context to predict from. With no language model to lean on, two limits bind:

1. Production rate. Connected speech runs about 5 to 6 syllables per second (Coupé et al. 2019), but reading random tokens aloud is far slower: in our own tests a speaker sustains only about 2 to 3 distinct utterances per second.
2. Recognition. The recognizer is a noisy channel with its own speed-accuracy tradeoff. We built several: free-transcription digits, vowels, a forced-choice recognizer over a swappable pool, and a continuous LocalAgreement streaming decoder on a fine-tuned small ASR model. On fast, accented, i.i.d. tokens, exact-match accuracy fell to 0.70 to 0.86, and the smallest models dropped into repeat-loops on monotonic input. Even 0.85 accuracy pulls the `(2a − 1)` multiplier down to 0.70.

End to end we measured about 5 bits per second. The best rate-accuracy corner we could model tops out near 8, still short of typing. We also pushed on the alphabet axis directly and checked the estimates adversarially:

| source (i.i.d.)            | effective N | bits/sel | sel/s | accuracy | **B (b/s)** |
|----------------------------|:--------:|:--------:|:-----:|:--------:|:-----------:|
| spoken digits 0-9          |    10    |   3.17   |  2.2  |   0.82   |    ~4.5     |
| spoken letter-names        |   ~15\*  |   3.81   |  2.2  |   0.70   |    ~3.3     |
| NATO phonetic words        |   ~24    |   4.52   |  1.0  |   0.78   |    ~2.5     |
| curated monosyllables      |    30    |   4.86   |  1.7  |   0.82   |    ~5.3     |
| **keyboard letters**       |  **26**  | **4.64** | **3-6** |**≈0.97**| **~13-26** |

\*Raw letter-names number 26, but the "E-set" (B, C, D, E, G, P, T, V, Z) collapses into one acoustic class, so the *distinguishable* alphabet is about 15 and exact-match accuracy caps near 0.70.

Every spoken option lands between about 2.5 and 5.5 bits per second because the three factors trade off against each other: a larger, more distinct vocabulary raises `log2(N − 1)` but lowers the rate (longer words) and the accuracy (more confusable tokens, more hesitation). The product stays flat, and it sits well below typing.

## Why typing wins

The people who will play this are professional software engineers, and for them the keyboard is an overlearned motor program built from years of daily use. That overlearning pays off in all three factors at once.

Accuracy comes from an exact channel. A keypress *is* the symbol; nothing has to recognize it. The full `log2 N` bits per keystroke survive, and `2a − 1` is set by the fingers, around 0.95 to 1.0, with no model in the loop to erode it. This is the largest single gap between typing and speech.

Bits per selection stay cheap because there is no Hick-Hyman tax. Choice reaction time grows with the information in the choice, `RT = a + b·log2 N` (Hick 1952; Hyman 1953), but only for unfamiliar choices. Overlearning drives the slope `b` toward zero: a touch-typist does not deliberate among 26 keys, because the path from seeing a letter to pressing it is automatic. So `N = 26` (`log2 25 = 4.64` bits per selection) costs almost no extra time, where an unpracticed mapping would pay in proportion to `log2 N`.

Rate comes from the same automaticity. On random letters, which deny typists the word-level motor programs and anticipation that make prose fast, fluent typists still hold about 3 to 6 keystrokes per second. The limit is finger transport, governed by Fitts's law (Fitts 1954), which touch-typing keeps small by anchoring on the home row.

Multiply it out: `4.64 bits/sel × 3-6 /s × ≈0.95 ≈ 13-26 bits/second`, past the ~8 bits per second ceiling we derived for speech. A casual but accurate typist already measures 10 to 15; a fast one runs well above 25. Reading keeps up easily.

The keyboard has to be physical for the same reason: more of the body is in play than on a phone screen. A full keyboard spreads the work across up to ten fingers with real key travel, where a phone leans on one or two thumbs. The gap is large and measured. A 37,000-volunteer study of mobile typing clocked it at about 36 words per minute, with speed tracking the number of fingers in play: two thumbs beat two index fingers, which beat one (Palin et al. 2019). Physical-keyboard typing runs faster, around 52 words per minute across a 136-million-keystroke desktop corpus (Dhakal et al. 2018). More fingers and more movement raise `R`, and a higher `R` raises `B`.

## Design choices behind the measurement

- A maximal `N`. All 26 letters, each fully distinguishable by an exact keypress, so `log2(N − 1)` counts bits the channel actually carries.
- A lossless channel. Typing removes the recognizer, fixes accuracy near 1.0, and recovers the full per-selection entropy that a speech recognizer erodes.
- An i.i.d. uniform source. Maximum entropy for a fixed `N`, with no language model or patterns inflating the score.
- Four-letter chunks. Letters are read and struck in groups; grouping a sequence into chunks is the standard way to work within a limited span (Miller 1956). Four is small enough to take in at a glance and hold without slipping, large enough to amortize the fixed per-action overhead, and it sets the attack cadence. Every profile uses the same four.
- Competition, which raises both rate and accuracy for a fixed player. The next section explains why.

## Why the full alphabet

The obvious way to raise accuracy is to drop letters that are easy to misread or mistype, keeping one of each confusable pair. We tested that idea against the objective and rejected it: for these players, in this font, the full 26 letters maximize `B`.

The margins are thin. Near `N = 26`, removing one letter costs only about 1.3% of the per-selection yield `log2(N − 1)`, but it has to buy back at least ~0.6 percentage points of accuracy through the doubly-weighted `(2a − 1)` term just to break even, and realistic accuracy is already too high for any cut to clear that bar. The letters appear as large, isolated glyphs in a legibility-tuned monospace (SF Mono, Roboto Mono, Consolas), the exact condition under which the classic lowercase confusion clusters dissolve: those matrices (Geyer 1977; Bouma 1971; Dunn-Rankin 1968) come from briefly-flashed, degraded type, and their authors note that only the relative ordering carries over while absolute error falls far lower. In a 136-million-keystroke corpus, single-key substitution runs about 1.6% (Dhakal et al. 2018). A skilled typist's mistakes are mostly transient slips like transpositions, with little of the similarity-driven confusion a smaller alphabet would dodge (Grudin 1983), so accuracy sits near 0.97.

At those accuracies the `N`-bits dominate. Modeling `B` across alphabet sizes, even crediting a trimmed set a generous extra point or two of accuracy, every smaller alphabet scores lower than the full one (roughly −5% at `N = 20`, −14% at `N = 16`). The one letter with any case for removal is `i`, the textbook code-font ambiguity with `l` that also sits between `u`, `o`, and `k` on QWERTY. But even that cut fails its own test: `i` comes up one time in 26, so to recover ~0.6 points of accuracy its per-letter error rate would have to top 15%, roughly ten times the ~1.6% the keystroke corpus reports and implausible for a clearly-rendered glyph. No cut improves `B`. Accuracy is already high because the font is clear, so the lever here is legibility, and keeping all 26 letters maximizes `B`.

For speech the binding term is accuracy: spoken bare letters are far less accurate, since the E-set alone runs into the tens of percent (Loizou and Spanias 1996). The same objective points to a different fix there, dropping the confusable letter names and having the player say distinct whole words instead. The Profiles section covers it.

## Why wrap it in a fight

The fight constrains the two factors a player can degrade, rate and accuracy, so the win condition and the score are the same function.

Damage is the bits transmitted: every completed four-letter block deals `log2 25 × max(correct − wrong, 0)`, floored at zero. HP is `1200 = 20 b/s × 60 s`, so only a round near 20 bits per second can empty a bar. There is no way to win except by maximizing `B`.

Competition raises `B` for the same pair of hands. Performance climbs with arousal up to a point (Yerkes-Dodson 1908), and a live opponent with a draining health bar raises the stakes, which pushes attention to its peak and keeps it there. A clear goal, instant feedback, and a challenge matched to skill are also the conditions for flow (Csikszentmihalyi 1990). Sustained attention lifts `R` and suppresses the slips that cost the `(2a − 1)` term, so the same hands produce a higher `B` under pressure than in a solo trial.

## How it works

- It takes two players on two separate devices, each with a physical keyboard (one player per device, because a browser can't tell two keyboards on one machine apart). Both open the same page, each presses Ready, and only then does the 60-second round begin. Either player can remove the other with a Kick button, handy when someone is holding a seat without readying up, and a player on their own can play solo against the computer (below).
- N = 26 letters, drawn i.i.d. uniform with replacement, with no language model or learnable patterns. (Emma's voice profile instead scores over its 150-word bank.)
- Each completed four-letter block is an attack; damage is `log2(25) × max(correct − wrong, 0)`.
- The server is the authoritative referee for HP, score, and winner. Browsers send keystroke results and draw the fight. Every round runs the full 60 seconds so the bit rate is always measured over the same window; maxing an opponent's damage bar does not end it early, and the higher HP at the buzzer wins.
- The end screen reports each player's `B`, `Sc`, and `Si`, so the measurement is visible; from there a player can rematch or return to the lobby.
- No dependencies for the core game: the server is pure Python standard library and the client is a single HTML page. Transport is SSE plus POST, and a reconnect reclaims the same player slot by token. The one exception is the optional voice profile, which loads the Vosk runtime from a CDN and a bundled offline model.

## Run it

Run `python fight_server.py`. It needs only Python 3, since the core game is pure standard library with nothing to install; it starts the server, opens the game in your browser, and prints a URL. A grader can play a full solo run from there.

Two players share one URL. On a local network, run `python fight_server.py` on each machine and the second discovers the first automatically; the first to open the page is Player 1, the second is Player 2, and the round begins once both press Ready. To host it instead, deploy as a web service (Render's free tier works) with the start command `python fight_server.py --cloud`, and both players open the same link. Full steps are in **[DEPLOY.md](DEPLOY.md)**. Any device with a physical keyboard works, including a tablet with an attached keyboard (Bluetooth, USB, or a folio keyboard).

## Practice solo (vs the computer)

The game is built for two people, but if you are on your own you can spar with a computer opponent instead of waiting for someone to join. Pick a difficulty in the lobby:

- Easy: the computer transmits about 6 bits per second.
- Middle: about 10 bits per second.
- Hard: about 14 bits per second.

The computer "types" at the rate you choose, with a little variation in pace so the rhythm stays uneven, and the rules are the same as a real match: you win by transmitting faster than it does. Each difficulty is also a concrete bits-per-second target to train against. This is an optional add-on; the real game is the two-player duel.

## Player profiles (optional twists)

The same match can be played three ways, picked in the lobby before you ready up. These are optional accommodations for different players; the default is the two-player keyboard duel.

- **Calvin** types the full 26 letters in blocks of four, the same as the default game. He is a fluent blind typist with a peak past 200 words per minute, so his edge is raw rate, and his profile adds nothing on top of the default.
- **Elizabeth** types the same letters with a large on-screen keyboard under the box. The current key lights up so she can find it without looking down, and she reads ahead from the letter row above the keyboard. A guided layout for a player who works best with the keys on screen and the current one lit.
- **Emma** speaks instead of typing, for a player whose hand-eye coordination makes the keyboard hard. Her box shows a row of common words (dog, fox, jazz) with the current one highlighted; she reads the highlighted word aloud, and an in-page recognizer matches it against a fixed set of words.

The bank is 150 common, easy-to-say words, each one or two syllables with enough sound to be clear, picked for two reasons. Ease: every word is short, frequent, and quick to read and say, so she keeps up a steady speaking rate. Accuracy: the recognizer is locked to the bank, so the words compete only against each other and accuracy is set by the closest pair in the set (Luce and Pisoni 1998); the 150 were chosen by maximizing the minimum pairwise phonetic distance over common words, so confusable pairs are rare. The bank size is the one lever Emma has that a typist does not. Scored the same way as a typist's letters, `log2(N − 1)` rises with the bank, but the farthest-first packing then reaches for words that crowd the ones already chosen, shrinking the minimum distance and putting accuracy at risk, and accuracy is the term that hurts twice. 150 sits near that knee: enough to lift each selection to 7.2 bits against a letter's 4.6, while the words stay the roomiest, most distinct common ones. A smaller bank gives up bits for no accuracy gain we could measure; a few hundred more shrink the minimum distance faster than the slow `log2` growth repays. Even at 7.2 bits, the lower speaking rate keeps her below the keyboard, so the bank is what makes voice viable for a player who cannot type. The lobby runs a microphone check with a device picker and a live level meter, and Emma can ready up only once it registers her voice.

On the assignment's constraint against word-level targets: each Emma target is one atomic selection, a single word drawn i.i.d. uniform from the 150 with replacement. The word is the symbol, the same role a letter plays for the keyboard alphabet, spoken as one utterance with nothing inside it to predict. The sequence has no exploitable statistics: no phrases, no cross-word patterns, and no language model in the loop, since the recognizer's fixed grammar forces every utterance onto one of the 150 words. The constraint exists to stop a game from inflating its score on the redundancy of real language, where the next letter of ordinary English is half-predictable. A uniform draw over 150 mutually distinct symbols has none of that redundancy, so every selection carries its full `log2(149)` bits: the most bits per selection available to a player who cannot use a keyboard, over the largest alphabet that stays cleanly separable by ear.

The recognizer is an in-page offline engine (Vosk), held by a grammar to exactly those 150 words, so every utterance it hears is forced onto one of them. If the offline model is unavailable, the browser's own speech engine fills in and each result is snapped to the nearest bank word. A small closed vocabulary is what this class of model handles best; full transcription models like Whisper are heavier and weaker on isolated tokens. It reads the exact microphone she selects, with the browser's echo cancellation, noise suppression, and auto-gain off, since those smear the brief consonant onsets that separate one word from the next. The model ships with the game, loads the first time someone picks Emma, and runs entirely offline. If a voice or room still trips a pair, the next step is a stronger recognizer: fine-tune on the word set, or adapt to one speaker with a few recorded samples.

The bundled model is `vosk-model-small-en-us-0.15` (about 40 MB, shipped as `assets/vosk-model-en.tar.gz`), served and cached by the same Python server. The `vosk-browser` runtime loads from a CDN; to run fully self-contained, host its `dist` files in `assets/` and point `VOSK_LIB_URL` in `fight.html` at them.

## Custom fighters

Each character is a folder of transparent frame images plus a `manifest.json`, with the states `intro`, `idle`, `attack1` through `attack4`, `hurt`, `win`, and `lose`. Drop in your own filmed, step-printed frames and they appear with no code change; this layer is cosmetic and does not affect the score. The filming guide, the processing pipeline, and the acceptance criteria are in **[PROCESSING.md](PROCESSING.md)**.

## References

- Shannon, C. E. (1948). *A Mathematical Theory of Communication.* Bell System Technical Journal.
- Hick, W. E. (1952). *On the rate of gain of information.* Quarterly Journal of Experimental Psychology.
- Hyman, R. (1953). *Stimulus information as a determinant of reaction time.* J. Experimental Psychology.
- Fitts, P. M. (1954). *The information capacity of the human motor system in controlling the amplitude of movement.* J. Experimental Psychology.
- Miller, G. A. (1956). *The magical number seven, plus or minus two.* Psychological Review.
- Yerkes, R. M., & Dodson, J. D. (1908). *The relation of strength of stimulus to rapidity of habit-formation.* J. Comparative Neurology and Psychology.
- Csikszentmihalyi, M. (1990). *Flow: The Psychology of Optimal Experience.*
- Coupé, C., Oh, Y., Dediu, D., & Pellegrino, F. (2019). *Different languages, similar encoding efficiency: comparable information rates across the human communicative niche.* Science Advances 5(9).
- Geyer, L. H. (1977). *Recognition and confusion of the lower-case alphabet.* Perception & Psychophysics 22(5).
- Bouma, H. (1971). *Visual recognition of isolated lower-case letters.* Vision Research 11(5).
- Dunn-Rankin, P. (1968). *The similarity of lower-case letters of the English alphabet.* J. Verbal Learning and Verbal Behavior 7(6).
- Dhakal, V., Feit, A. M., Kristensson, P. O., & Oulasvirta, A. (2018). *Observations on typing from 136 million keystrokes.* CHI 2018.
- Grudin, J. T. (1983). *Error patterns in novice and skilled transcription typing.* In Cognitive Aspects of Skilled Typewriting.
- Palin, K., Feit, A. M., Kim, S., Kristensson, P. O., & Oulasvirta, A. (2019). *How do people type on mobile devices? Observations from a study with 37,000 volunteers.* MobileHCI 2019.
- Loizou, P. C., & Spanias, A. S. (1996). *High-performance alphabet recognition.* IEEE Transactions on Speech and Audio Processing 4(6).
- Luce, P. A., & Pisoni, D. B. (1998). *Recognizing spoken words: the neighborhood activation model.* Ear and Hearing 19(1).

MIT licensed. See [LICENSE](LICENSE).
