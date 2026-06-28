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

`N` is the alphabet size; `Sc` and `Si` are the correct and incorrect selections in `t` seconds. A selection drawn uniformly from `N` options carries up to `log2 N` bits (Shannon 1948); the `N − 1` is a conservative shave for an error-correction key, and the `max(·, 0)` floor makes an error forfeit a selection's worth of credit. Reading the formula gives three levers, and a good design pushes all of them at once:

- the bits per selection, `log2(N − 1)`, which grows only with the log of `N`, so a wider alphabet pays slowly;
- the rate, how many selections you make per second, set by how fast the effector can act;
- the accuracy, how many of them land in `Sc`. An error is doubly costly, since it both misses `Sc` and adds to `Si`, so accuracy below about 0.9 falls off fast.

These three trade off, so a good interface keeps all of them high for whoever is playing.

## Input modality

The player's input to the game is their own physical output, so the modality question is which output channel moves the most bits. Reading the target hardly counts toward that, since the eye is the fastest channel into a person, which leaves the hands or the voice as the bottleneck. The game offers two channels: a physical keyboard by default, and a voice mode.

### The keyboard

For anyone who types daily, the keyboard is the obvious default: an overlearned motor program where the keypress is the symbol, so the full `log2 N` bits survive at near-perfect accuracy. The choice costs almost no time, since Hick-Hyman reaction time grows only for unfamiliar mappings (Hick 1952; Hyman 1953), and rate is set by finger transport (Fitts 1954), spread across ten fingers on a physical board where a phone has only one or two thumbs (Palin et al. 2019; Dhakal et al. 2018). A fluent typist lands around 13 to 26 bits per second.

The alphabet is all 26 letters. Near `N = 26`, dropping a letter to remove a confusable pair costs about 1.3% of `log2(N − 1)`, which the doubly-weighted accuracy term has to repay with at least ~0.6 points of accuracy just to break even, and real accuracy is already too high for any cut to clear that bar. The letters render as large, isolated glyphs in a legibility-tuned monospace, the condition under which the classic lowercase confusion clusters dissolve: the matrices of Geyer (1977), Bouma (1971), and Dunn-Rankin (1968) come from briefly-flashed, degraded type, and only their relative ordering carries over. In a 136-million-keystroke corpus, single-key substitution runs about 1.6% (Dhakal et al. 2018), and skilled typists' slips are mostly transpositions, with little of the similarity confusion a smaller alphabet would avoid (Grudin 1983), so accuracy sits near 0.97. Modeling `B` across alphabet sizes, even crediting a trimmed set extra accuracy, every smaller alphabet scores lower (about −5% at `N = 20`, −14% at `N = 16`), so `N = 26` and `log2 25 = 4.64` bits per selection.

Two modes share the keyboard, picked in the lobby. **Calvin**, the default, is plain unobstructed typing, the shortest path to a high `B`. **Elizabeth**, the guided mode, adds a large on-screen keyboard under the box: the current key lights up and is easy to locate without looking down, and the upcoming letters sit in the row above. (The brief describes Calvin as a fluent blind typist past 200 words per minute, and Elizabeth as a balanced player who values a well-designed interface.)

### Voice

The keyboard assumes hands that cooperate. For a player with worse-than-average hand-eye coordination, both the rate and the accuracy fall, slower keying and more slips, so a voice mode can do better. That mode is **Emma**'s: the box shows a row of common words with one highlighted, the player reads it aloud, and an in-page recognizer matches it against a fixed set. (The brief describes her coordination as worse than average.)

Speech is harder to recognize on an i.i.d. stream, which strips the language context a recognizer leans on (Coupé et al. 2019). Whole words read back more reliably than spelled-out letters, which collapse the E-set (Loizou and Spanias 1996), and a bank of them carries more bits per selection than digits or letters; after trying digits, letter-names, and NATO codes I settled on 150 common, distinct one- or two-syllable words, picked by maximizing the minimum pairwise phonetic distance (Luce and Pisoni 1998). Their count is the same bits-versus-accuracy trade as the keyboard alphabet, since a grammar locked to the bank sets accuracy by its closest pair: 150 sits at the knee, 7.2 bits per selection against a letter's 4.6, where fewer words give up bits and more crowd that pair and erode accuracy.

Each word is one symbol the recognizer never breaks into letters, drawn i.i.d. uniform and scored whole for its full `log2(149)` bits. That keeps the rule against word-level targets satisfied: there is no English redundancy to bank inside a symbol, and a random sequence has none across words either. The recognizer is an offline engine (Vosk) held by a grammar to exactly those 150 words, reading the chosen microphone with echo cancellation, noise suppression, and auto-gain off, since those smear the consonant onsets that separate one word from the next; if it is unavailable, the browser's own speech engine fills in, snapped to the nearest bank word.

## The game

- The source is i.i.d. uniform: targets are drawn with replacement, with no patterns and no language model, so the sequence has no exploitable statistics and every selection carries its full entropy.
- Letters group into four-letter blocks, a size that fits a limited span (Miller 1956), holds at a glance, and sets the attack cadence.
- The bit rate updates every frame, and the single 60-second round reports the final `B`, `N`, `Sc`, and `Si`.
- Damage is the bits you transmit: a block deals `log2 25 × max(correct − wrong, 0)`, HP is `1200 = 20 b/s × 60 s`, and the round always runs the full minute, so the only way to win is to maximize `B`. A live opponent raises `B` for the same hands, since arousal lifts performance up to a point (Yerkes-Dodson 1908) and a clear goal with instant feedback sustains the attention and flow (Csikszentmihalyi 1990) that lift the rate and suppress errors.
- A single player, a grader included, takes a scored run against a paced bot (about 6, 10, or 14 b/s); the bot doubles as a bits-per-second target to train against.

## Running it

Run `python fight_server.py` (Python 3, no dependencies, since the core is pure standard library). It opens the game in a browser. A single player, a grader included, picks a profile, starts a solo round against the practice bot, and plays the 60 seconds; the final `B`, `N`, `Sc`, and `Si` show at the buzzer.

For two players, both open the same URL: the first becomes Player 1, the second Player 2, and the round begins once both press Ready. On a local network each machine runs the server and the second discovers the first automatically; to host it, deploy as a web service with `python fight_server.py --cloud` (full steps in **[DEPLOY.md](DEPLOY.md)**). The server keeps the official score and runs the 60-second clock. Character art is a drop-in folder of frames per fighter and is cosmetic (see **[PROCESSING.md](PROCESSING.md)**).

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
