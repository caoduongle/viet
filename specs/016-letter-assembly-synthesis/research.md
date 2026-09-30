# Research & Architecture Decisions: Letter-Level Handwriting Assembly & Fallback Synthesis

**Feature**: `016-letter-assembly-synthesis`  
**Date**: 2026-09-30  
**Status**: Completed  

---

## 1. Vietnamese Letter Decomposition & Orthography

### Context
In the existing codebase, `text_utils.tone_info(key)` uses Unicode NFD decomposition to identify tone marks (`TONES`) and hats (`\u0302\u0306`). However, NFD splits Vietnamese letters with diacritics into base ASCII plus combining marks (e.g. `ă` into `a` + `\u0306`, `ơ` into `o` + `\u031b`), which does not reflect human handwriting units: a Vietnamese speaker writes `ă`, `â`, `đ`, `ê`, `ô`, `ơ`, `ư` as complete letter glyphs, not as separate diacritic strokes over latin letters.

### Decision
Implement `split_letters(word: str) -> tuple[list[str], str, int]`:
1. Normalize input word to NFC.
2. Extract tone mark `T` and vowel index `vi` using existing `strip_tone(word)` and `tone_info(word)`.
3. The remaining unaccented word in NFC contains the exact 29 Vietnamese base letters (`a, ă, â, b, c, d, đ, e, ê, g, h, i, k, l, m, n, o, ô, ơ, p, q, r, s, t, u, ư, v, x, y`) and uppercase counterparts.
4. Return `(letters, tone, vowel_index)` where each element of `letters` is a single atomic character unit in NFC.

### Rationale
- Matches the standard Vietnamese alphabet (29 letters).
- Users draw letters naturally (e.g. drawing `đ` with its crossbar, or `ă` with its breve) in one handwriting canvas session.
- Only the 5 tone marks (`huyền, sắc, hỏi, ngã, nặng`) are detached as floating marks, identical to the existing `_harvest` and `substitute` behavior.

### Alternatives Considered
- *Decomposing vowels into ASCII + accent marks (e.g., `a` + breve)*: Rejected because drawing an isolated breve or horn on a separate canvas cell is unnatural for Vietnamese writers, misaligns baseline positioning, and introduces floating stroke placement errors.
- *Full word syllables only*: Rejected as that is the exact limitation of the current system requiring hundreds of word samples.

---

## 2. Greedy Set-Cover Ranking for Missing Letters

### Context
When a user writes a document with missing words, presenting a random or alphabetical list of missing letters does not provide the highest teaching efficiency. A greedy ranking shows the letters that unlock the greatest number of unlearned words first.

### Decision
Implement `missing_letters_ranked(text: str, bank: Bank, strict_case: bool = False) -> list[tuple[str, int, list[str]]]`:
1. Scan text for words where `bank.can(w)` is False (cannot be fulfilled by whole words or root substitution).
2. For each missing word, decompose into required letter units and tone mark.
3. Determine which letter units and tone marks are not in `bank.letters` or `bank.marks`.
4. Count the number of unlearned words each missing unit would help unlock.
5. In greedy order, iteratively select the letter unit that covers the most remaining unlearned words, recording the unlocked words.
6. Return `[(letter_or_tone, unlock_count, [unlocked_words]), ...]`.

### Rationale
Maximizes user productivity: drawing just 5–10 high-value letters (e.g. `n, h, t, c, a`) immediately unlocks 60–80% of missing vocabulary.

---

## 3. Storage Schema Evolution (Schema v4) & Concurrency Safety

### Context
The handwriting bank is stored as gzip-compressed JSON (`.json.gz`). Currently, `CURRENT_VERSION = 3` in `bank_schema.py` validates `words`, `digits`, `punct`, `symbols`. Adding a `letters` container requires schema validation, migration from older versions, and multi-process safety.

### Decision
1. Increment `CURRENT_VERSION = 4`.
2. Add migration step `_migrate_v3_to_v4(d: dict) -> dict` in `bank_schema.py`:
   - Sets `d["schema_version"] = 4`.
   - Initializes `d.setdefault("letters", {})`.
3. Add `letters: dict` to `REQUIRED_METADATA_KEYS`.
4. Update `merge_bank_dicts()` in `bank.py`:
   - Include `"letters"` in the synchronized categories: `("words", "digits", "punct", "symbols", "letters")`.
   - Apply tombstones to remove deleted letters.
   - Deduplicate letter samples using existing `_sample_signature()`.
5. Support `drop_letter(label: str)` and ensure `drop(word: str)` cleans up `letters` when applicable, recording tombstones with generation increment.

### Rationale
- Full backward compatibility: v1, v2, and v3 bank files load, migrate in-memory, and validate without errors.
- Multi-process safety: parallel GUI and CLI operations with `.lock` and generation counter preserve letter additions and deletions without lost updates.

---

## 4. Letter Assembly & Baseline Alignment Algorithm

### Context
Synthesizing a word from individual letter samples requires:
- Baseline alignment ($y = 0$).
- Horizontal spacing and kerning between letters.
- Natural random jitter.
- Tone mark attachment (above or below the vowel).
- Dot suppression for letter `i` when an upper tone is applied.

### Decision
Implement `Writer.assemble_word(core: str) -> tuple[list[Stroke], float] | None`:
1. **Decomposition**: Get `letters, T, vi = split_letters(core)`.
2. **Availability Check**:
   - For each letter $c \in letters$: check `bank.letters.get(c)`.
   - If missing and `self.loose and c.isupper()`: fall back to `bank.letters.get(c.lower())`.
   - If any letter is missing, or if $T \ne ""$ and `bank.marks.get(T)` is empty, return `None`.
3. **Glyph Layout**:
   - Iterate over letters. For letter $k$, pick sample `inst = self.pick(bank.letters[c], "let:" + c)`.
   - Place sample at current $x$: `placed_strokes = [shift(s, x, 0) for s in inst["s"]]`.
   - Compute kerning overlap: let $overlap = 0.08 \cdot xh$ (or $0.5 \cdot \text{avg\_gap}$).
   - Advance $x \mathrel{+}= \max(0.1, inst["w"] - overlap) + \text{jitter\_offset}$.
4. **Tone Mark Placement**:
   - If $T \ne ""$ and $vi \ge 0$:
     - Pick tone sample $m$ from `bank.marks[T]`.
     - Calculate vowel center $x_v$ from the horizontal position of letter $vi$.
     - If upper tone (huyền, sắc, hỏi, ngã):
       - If $letters[vi] == "i"$: suppress the dot stroke of letter `i` in the assembled body using the bounding box height filter (`bbox(st)[3] < -0.9 * xh`).
       - $y_{top} = \text{near\_extreme}(body, x_v, \min) + m["dy"]$.
       - Append shifted tone mark at $(x_v + m["dx"], y_{top})$.
     - If lower tone (nặng):
       - $y_{bot} = \max(0.0, \text{near\_extreme}(body, x_v, \max)) + m["dy"]$.
       - Append shifted tone mark at $(x_v + m["dx"], y_{bot})$.
5. **Return**: Return `(body, total_width)`.

### Rationale
- Reuses the battle-tested tone positioning math from `substitute()` and `_harvest()`.
- Guarantees natural baseline alignment because all letter samples have baseline $y = 0$.
- Prevents collision of tone marks with the dot on `i`.

---

## 5. Golden Master Invariance Strategy

### Context
`tests/test_golden_master.py` asserts exact SHA-256 hashes for `.xopp` documents rendered under various configurations. Any change to the default rendering pipeline breaks this test.

### Decision
1. Add `assemble_letters: bool = False` to `WriteOptions`.
2. In `Writer.word(core)`:
   ```python
   # 1. Exact whole word
   for c in variants:
       if c in self.b.words:
           return self.pick(self.b.words[c], c)
   # 2. Root substitute
   for c in variants:
       r = self.substitute(c)
       if r:
           return r
   # 3. Letter assembly (ONLY if enabled)
   if self.assemble_letters:
       r = self.assemble_word(core)
       if r:
           return r
   return None
   ```
3. When `assemble_letters=False`, execution flow is 100% identical to the legacy pipeline.
4. Golden master tests use default `WriteOptions()` where `assemble_letters=False`, guaranteeing zero regression.

---

## 6. Summary of Architectural Decisions Table

| Component | Choice | Justification |
|---|---|---|
| Letter Units | 29 Vietnamese NFC characters + uppercase + 5 TONES | Natural handwriting units; aligns with Vietnamese alphabet |
| Ranking Heuristic | Greedy set-cover on unlearned words | Minimizes teaching effort to unlock maximum vocabulary |
| Storage Schema | Schema v4 (`letters: dict`) with v1-v3 migration | Backward compatible, clean validation, multi-process safe |
| Resolution Order | Whole word $\rightarrow$ Root substitute $\rightarrow$ Letter assembly $\rightarrow$ Blank gap | Whole words have superior ligatures; letters serve as reliable fallback |
| Default State | `assemble_letters = False` in `WriteOptions` | 100% Golden Master parity; zero regression for legacy users |
| UI Controls | Checkbox on WriteTab, letter queue in TeachTab, letter inventory on BankTab | Clean MVC separation; user control across GUI and CLI |
