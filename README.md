# Street Typer

> A two-player typing fight built to maximize the information rate a human can push through an interface. The damage you deal is the bits you transmit, so the player who moves the most information per second wins.

[![Play the game](https://img.shields.io/badge/play-street--typer.onrender.com-ff7a18.svg)](https://street-typer.onrender.com/)
&nbsp;![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
&nbsp;![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB.svg?logo=python&logoColor=white)
&nbsp;![Dependencies: none](https://img.shields.io/badge/dependencies-none%20(stdlib)-brightgreen.svg)
&nbsp;![Players: 2](https://img.shields.io/badge/players-2-orange.svg)
&nbsp;![Objective: max bits/sec](https://img.shields.io/badge/objective-max%20bits%E2%81%84sec-8a2be2.svg)

Street Typer is a single 60-second round, scored by the bit rate the player achieves.

## The objective

The game maximizes the achieved bit rate the assignment defines:

```
B = log2(N − 1) · max(Sc − Si, 0) / t       [bits / second]
```

`N` is the alphabet size; `Sc` and `Si` are the correct and incorrect selections in `t` seconds. A selection drawn uniformly from `N` options carries up to `log2 N` bits (Shannon 1948); the `N − 1` is a conservative shave for an error-correction key, and the `max(·, 0)` floor makes an error forfeit a selection's worth of credit. The formula factors into the only three quantities a player controls:

```
B = log2(N − 1) · R · (2a − 1),   R = (Sc + Si) / t,   a = Sc / (Sc + Si)
```

- `log2(N − 1)`, the bits per selection, grows with the log of `N`, so a wider alphabet pays slowly.
- `R`, the selections per second, is set by how fast the effector can act.
- `2a − 1`, the share of information that survives, is linear in accuracy with slope 2, since an error both forfeits its credit and is subtracted, so accuracy below about 0.9 falls off fast.

The three trade against each other, so the design has to push all of them at once.

## Input modality

A round is a stream of selections the player produces, so output bandwidth is the binding constraint. Reading the next target is near-instant through vision, the fastest input a person has, so the game shows targets plainly and the whole budget goes to output. The open question is which output channel carries the most bits per second.

**Speech is the obvious candidate, and the measurements rule it out.** Natural speech runs about 39 bits per second (Coupé et al. 2019), but that is entropy *given context*, most of it predictable from the words before it. An i.i.d. uniform source strips that context away, and two limits bind. Production: reading random tokens aloud, I sustain only about 2 to 3 distinct utterances per second. Recognition: the recognizer is a noisy channel of its own. I built several, including free-transcription digits and vowels, a forced-choice decoder over a swappable pool, and a LocalAgreement streaming decoder on a fine-tuned small model; on fast, accented, i.i.d. tokens, exact-match accuracy fell to 0.70 to 0.86, and the smallest models looped on monotonic input. End to end I measured about 5 bits per second, with an optimistic ceiling near 8. Pushing on the alphabet does not rescue it:

| source (i.i.d.)            | effective N | bits/sel | sel/s | accuracy | **B (b/s)** |
|----------------------------|:--------:|:--------:|:-----:|:--------:|:-----------:|
| spoken digits 0-9          |    10    |   3.17   |  2.2  |   0.82   |    ~4.5     |
| spoken letter-names        |   ~15\*  |   3.81   |  2.2  |   0.70   |    ~3.3     |
| NATO phonetic words        |   ~24    |   4.52   |  1.0  |   0.78   |    ~2.5     |
| curated monosyllables      |    30    |   4.86   |  1.7  |   0.82   |    ~5.3     |
| **keyboard letters**       |  **26**  | **4.64** | **3-6** |**≈0.97**| **~13-26** |

\*Raw letter-names number 26, but the "E-set" (B, C, D, E, G, P, T, V, Z) collapses into one acoustic class (Loizou and Spanias 1996), so the *distinguishable* alphabet is about 15 and accuracy caps near 0.70.

Every spoken option lands between about 2.5 and 5.5 bits per second: a larger, more distinct vocabulary raises `log2(N − 1)` but costs rate (longer words) and accuracy (more confusable tokens), so the product stays flat.

**Typing wins because the keyboard is overlearned.** For anyone who types daily, the keyboard is a motor program built over years, and that pays off in all three factors at once.

- Accuracy comes from an exact channel. A keypress *is* the symbol, so nothing has to recognize it: the full `log2 N` bits survive and `2a − 1` sits around 0.95 to 1.0, set by the fingers. This is the largest single gap over speech.
- Bits per selection stay cheap. Choice reaction time grows with `log2 N` only for unfamiliar choices (Hick 1952; Hyman 1953); overlearning drives the slope toward zero, so a touch-typist pays almost no extra time for 26 keys.
- Rate comes from the same automaticity. On random letters, which deny typists the word programs that make prose fast, fluent typists still hold 3 to 6 keystrokes per second, limited by finger transport (Fitts 1954) and kept short by the home row.

The three factors multiply to 13 to 26 bits per second, past the speech ceiling, and in my own testing a casual but accurate typist measures 10 to 15, a fast one well above 25.

The keyboard has to be physical because more of the body is in play. A full keyboard spreads work across up to ten fingers with real key travel, where a phone leans on one or two thumbs: about 36 words per minute on mobile against roughly 52 on a desktop, with speed tracking the number of fingers (Palin et al. 2019; Dhakal et al. 2018). More fingers raise `R`, and a higher `R` raises `B`.

One assumption runs under all of this: `B` is per-player. `R` and `a` are properties of the effector, and the keyboard maxes both for a practiced typist. A player with worse-than-average hand-eye coordination pays the keyboard in those same two terms, slower keying and more slips, so its lead narrows. Speech sits near 5 b/s for anyone, set by the recognizer and the speaking rate, so once poor coordination drags a player's keyboard below that, voice is the better channel. That is why the game ships two input modalities: typing by default, and a voice mode for the players the keyboard serves worst, covered under Player modes.

## Alphabet size: N = 26

The keyboard fixes the natural alphabet at 26 letters, and the arithmetic says to keep all of them. Near `N = 26`, dropping a letter to remove a confusable pair costs about 1.3% of `log2(N − 1)`, which the doubly-weighted accuracy term has to repay with at least ~0.6 points of accuracy just to break even. Real accuracy is already too high for any cut to clear that bar. The letters render as large, isolated glyphs in a legibility-tuned monospace, the condition under which the classic lowercase confusion clusters dissolve: the matrices of Geyer (1977), Bouma (1971), and Dunn-Rankin (1968) come from briefly-flashed, degraded type, and only their relative ordering carries over. In a 136-million-keystroke corpus, single-key substitution runs about 1.6% (Dhakal et al. 2018), and skilled typists' slips are mostly transpositions, with little of the similarity confusion a smaller alphabet would avoid (Grudin 1983), so accuracy sits near 0.97. Modeling `B` across alphabet sizes, even crediting a trimmed set extra accuracy, every smaller alphabet scores lower (about −5% at `N = 20`, −14% at `N = 16`). The one letter with any case for cutting is `i`, but to repay its 1-in-26 share it would need a 15% error rate, ten times what the corpus shows. So `N = 26`, and `log2 25 = 4.64` bits per selection.

## The rest of the design

- **An i.i.d. uniform source.** Targets are drawn uniformly with replacement, with no patterns and no language model, so the sequence has no exploitable statistics and every selection carries its full entropy.
- **Four-letter blocks.** Grouping the stream into chunks is the standard way to work within a limited span (Miller 1956); four is small enough to hold at a glance, large enough to amortize the per-action overhead, and it sets the attack cadence.
- **A live readout and a fixed window.** The bit rate updates every frame, and a single 60-second round reports the final `B`, `N`, `Sc`, and `Si`.
- **A two-player fight.** Damage is bits: a block deals `log2 25 × max(correct − wrong, 0)`, HP is `1200 = 20 b/s × 60 s`, and the round always runs the full minute, so the only way to win is to maximize `B`. Competition raises `B` for the same hands, since arousal lifts performance up to a point (Yerkes-Dodson 1908) and a clear goal with instant feedback sustains the attention and flow (Csikszentmihalyi 1990) that lift `R` and suppress errors. A solo mode against a paced bot (about 6, 10, or 14 b/s) gives a target to train against when no opponent is around.

## Player modes

Three modes share the lobby, each built for a different kind of player. They are optional; the default is the keyboard duel.

- **Calvin**, the raw-speed mode, is the default game unchanged: plain, unobstructed typing is the shortest path to a high `B`, so the mode adds nothing on top. (The brief describes a fluent blind typist past 200 words per minute.)
- **Elizabeth**, the guided mode, adds a large on-screen keyboard under the box. The current key lights up and is easy to locate without looking down, and the upcoming letters sit in the row above. (The brief describes a balanced player who values a well-designed interface.)
- **Emma**, the voice mode, swaps typing for speech. For a player whose hand-eye coordination is below average, the keyboard's rate and accuracy edge shrinks, so speech can be the stronger channel for them. The box shows a row of common words with one highlighted; the player reads it aloud, and an in-page recognizer matches it against a fixed set. (The brief describes Emma's coordination as worse than average.)

The symbols are whole words because that is what a speech recognizer reads most reliably. Spelling out letters runs into the E-set, where nine letter-names collapse into one acoustic class and accuracy caps near 0.70 (the table above); whole words sidestep that and hold accuracy around 0.82, and the bank turns their distinctness into bits, more per selection than ten digits or fifteen distinguishable letter-names reach. The 150 words are common and one or two syllables, chosen by maximizing the minimum pairwise phonetic distance (Luce and Pisoni 1998). Picking the size is the same bits-versus-accuracy trade as the keyboard alphabet: `log2(N − 1)` rises with the bank, but a grammar locked to it sets accuracy by the closest pair, and adding words crowds that pair. 150 sits near the knee, at 7.2 bits per selection against a letter's 4.6, while the words stay the most distinct common ones; a smaller bank forfeits bits for no accuracy I could measure, and a few hundred more shrinks the minimum distance faster than the slow `log2` growth repays.

Each of the 150 words is one symbol, the role a letter plays for the keyboard, and the recognizer never breaks it into letters. The rule against word-level targets forbids scoring a real word letter by letter and banking the redundancy of English; here a word is one atomic selection drawn i.i.d. uniform and scored whole for its full `log2(149)` bits, so there is no redundancy inside a symbol and none across the random sequence to exploit.

The recognizer is an offline engine (Vosk) held by a grammar to exactly those 150 words, reading the chosen microphone with echo cancellation, noise suppression, and auto-gain off, since those smear the consonant onsets that separate one word from the next. If it is unavailable, the browser's own speech engine fills in, snapped to the nearest bank word. The model ships with the game.

## Running it

Run `python fight_server.py` (Python 3, no dependencies, since the core is pure standard library). It serves the game, opens a browser, and prints a URL, and a grader can take a full solo run from there. For two players, both open the same URL: the first becomes Player 1, the second Player 2, and the round begins once both press Ready. On a local network each machine runs the server and the second discovers the first automatically; to host it instead, deploy as a web service with `python fight_server.py --cloud` (full steps in **[DEPLOY.md](DEPLOY.md)**). The server keeps the official score and runs the 60-second clock. Character art is a drop-in folder of frames per fighter and is cosmetic (see **[PROCESSING.md](PROCESSING.md)**).

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
