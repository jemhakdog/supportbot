# CAPSULES — part 1 (stage 1, directions A–E)

All five capsules describe the same working copy (`WORKING-COPY.md`) used verbatim in every direction.

## Direction A
- Premise: the app's inbox is read as an operations ledger: every label word becomes a right-aligned key and everything that belongs to it sits flush left in a value column, so the vocabulary of the tool is filed rather than displayed.
- Fonts: display / supporting / small = `"Courier New", ui-monospace, Menlo, Consolas, monospace` (single family for the whole page). Source = local system monospace; license varies with OS install, ships with desktop systems; falls back to `monospace`.
- Scale & case: name 44px bold, lowercase, 0.48em tracking; purpose 17px regular, sentence case, 54ch; keys 17px bold sentence case, 18ch wide, right-aligned; values 17px regular, sentence case, 58ch; in-row figures 27px. Line height 1.55 body, 1.1 on figures. Left-aligned throughout, no centering; rows break only at the middot separators.
- Space: page padding 54/72/104px; purpose indented by the key column (18ch + 34px) so it aligns with the value column; row gap 36px; key/value gap 34px; 74px gap between purpose and first row; wide empty right field beyond 58ch values.
- Color: canvas `#efece2` (entire page); one text color `#17150f` (100% of letterforms: name, purpose, keys, values, figures). Depth = 1.
- Signature: a right-aligned key gutter against a flush-left value column, with the metric figures (`4`, `60`, `0-100%`, `$0`, `FTS5`) set at 27px inside 17px lines, so measurement reads louder than its label in a single ink.
- Invariants: one ink only; key/value two-column alignment; Courier family; the figure-vs-label size inversion; no rules or dividers between rows (whitespace only).
- Assumptions & risks: key/value pairings (e.g. `Inbox` → status list, `Ticket` → column words) are inferred from app semantics, not printed in the copy; tall figure spans may lengthen two rows; Courier at 17px gives a long page.
- Round 2: keep the ledger pairing and single ink; if any figure is restyled, it must stay inside a value line and never gain a color of its own.

## Direction B
- Premise: triage is routing, so the eight status words walk down the page in eight successively deeper indents while everything the machine merely names stays flush left at the top — the copy's own state list performs the descent it describes.
- Fonts: display / supporting / small = `Helvetica, Arial, "Helvetica Neue", sans-serif`. Source = local system sans; license per OS; falls back to `sans-serif`.
- Scale & case: name 88px bold, lowercase, -0.035em tracking, line-height 0.96; purpose 25px regular sentence case, 41ch; vocabulary line 12.5px bold UPPERCASE, 0.19em tracking, line-height 2.5, 74ch; notes 14.5px, line-height 1.9; states 30px bold sentence case, line-height 1.5. Everything flush left; the only movement is the 7% step per state line.
- Space: page padding 62/70/100px; 58px between purpose and vocabulary; 78px between notes and the first state; state lines spaced by their own 1.5 leading plus indent, leaving a growing empty field in the lower left.
- Color: canvas `#e6e9ec`; primary `#101316` (name, purpose, vocabulary, notes ≈ 60% of text); secondary `#8c3316` (the eight state lines ≈ 40%, in the dominant lower-right position). Depth = 2.
- Signature: the state list descending on a 7% indent staircase from `All` at the margin to `No tickets in this view.` near the right edge, in the second ink, against a flat flush-left top block.
- Invariants: two inks with the state list owning the secondary color; the staircase geometry (7 steps, constant increment); Helvetica as the only family; uppercase reserved for the vocabulary line.
- Assumptions & risks: the deepest indent must not push `No tickets in this view.` past the right margin at narrow widths; sentence-case states and uppercase vocabulary must stay visually distinct from direction D's caps layers.
- Round 2: build the state list as an indented sequence with equal increments; do not convert it into badges, pills, or a table.

## Direction C
- Premise: the vocabulary the retriever works from runs as a vertical rail down the left edge while the human-facing text — declaration, states, decisions — reads horizontally beside it; retrieval alongside the draft.
- Fonts: display / supporting = `Georgia, "Times New Roman", serif` (purpose set in genuine italic); small = same stack at 13–14.5px. Source = local system serif; license per OS; falls back to `serif`.
- Scale & case: name 58px bold lowercase; purpose 25px italic sentence case, line-height 1.7, 43ch; rail 13px UPPERCASE, 0.26em tracking, line-height 2.7 in vertical writing mode; states 31px sentence case, 34ch; decisions 22px, 0.06em tracking; figures 14.5px, 0.12em tracking. Horizontal text is flush left; only the rail is vertical.
- Space: page padding 58/78/88/56px; rail height 76vh with the field beside it; 60px gap between rail and field; 66px under the purpose; 54px under states; 62px under decisions; rail wraps into columns inside its fixed height.
- Color: canvas `#14161a`; primary `#ece7db` (name and purpose ≈ 45% of text mass); secondary `#8fa2b0` (vertical rail and figure line ≈ 45%); accent `#e5a13a` (state list and decision words ≈ 10%, but the largest horizontal type after the name). Depth = 3.
- Signature: a full-height vertical uppercase rail of the label vocabulary running against horizontally set italic prose, with the state and decision words in the accent ink occupying the widest type on the field.
- Invariants: three inks and their jobs (prose / vocabulary / states-and-decisions); the vertical rail; the italic purpose; dark canvas; no accent on the name or the prose.
- Assumptions & risks: rail wrapping depends on viewport height; italic Georgia at 25px needs a controlled 43ch measure; accent share is small in word count, so it must keep its large size to remain a real role.
- Round 2: keep the rail as live vertical text of the label list, never as a sidebar panel or colored strip.

## Direction D
- Premise: the copy arrives in four strata — what the tool is, what it names, what it operates and measures, what state a ticket is in — and each stratum is printed in its own ink at its own scale, four passes over one sheet.
- Fonts: display / supporting / small = `"Segoe UI", "Helvetica Neue", system-ui, sans-serif`. Source = local system sans; license per OS; falls back to `sans-serif`.
- Scale & case: name 122px bold lowercase, -0.045em, line-height 0.9; purpose 29px sentence case, 35ch; vocabulary 16px sentence case, 0.05em, line-height 2.15, 70ch; operation words 15px bold UPPERCASE at 0.15em beside figures at 66px bold; decisions 19px at 0.1em; states 34px bold UPPERCASE at 0.07em, 26ch. All flush left, stacked bands.
- Space: page padding 50/74/96px; 26px under the name; 70px under the purpose; 68px under the vocabulary; 66px under the operations line plus 40px above the decisions; states close the page with no bottom ornament; wide ragged right beyond 35ch purpose.
- Color: canvas `#f4f2ed`; primary `#17140f` (name + purpose ≈ 45%); secondary `#37475f` (vocabulary ≈ 25%); tertiary `#2f6b4f` (figures and decisions ≈ 20%); accent `#a83a1a` (state list ≈ 10%, closing the page at 34px). Depth = 4.
- Signature: 66px figures interleaved on the same lines as 15px uppercase operation words — `60`, `0-100%`, `$0`, `FTS5` outweighing the words that qualify them — above a rust state block that ends the page.
- Invariants: four inks, each owning one stratum; the figure/operation-word size inversion; the 122px lowercase name; uppercase reserved for machine-layer strata; flush-left band stacking.
- Assumptions & risks: mixed 15px/66px inline runs wrap unpredictably at narrow widths; the accent covers few words, so its size must not shrink; uppercase state list must not read as a heading borrowed from direction B.
- Round 2: keep the four strata in four inks; if any stratum is regrouped, the ink must follow the stratum, never a highlighted word.

## Direction E
- Premise: knowledge-gap tracking means the record of absence is the content — so the empty-state sentence carries the largest type on the page while the product name sits at the smallest, everything set in one ink on an unbleached ground.
- Fonts: display / supporting / small = `"Palatino", "Book Antiqua", Georgia, serif`. Source = local system serif; license per OS; falls back to `serif`.
- Scale & case: name 14px regular, lowercase, 0.6em tracking, centered; purpose 20px sentence case italic-free, line-height 1.85, 44ch; vocabulary 13px sentence case, 0.09em tracking, 0.34em word spacing, line-height 2.4, 58ch; state run 14.5px UPPERCASE, 0.24em tracking; gap sentence 74px bold, 15ch; notes 12.5px, 0.14em tracking. Everything centered.
- Space: page padding 74/28/92px; 60px under the name; 58px under the purpose; 70px under the vocabulary; 30px between the state run and the gap sentence; 66px after it; measures grow then contract (44ch → 58ch → 56ch → 15ch → 56ch).
- Color: canvas `#ddcaa2`; one text color `#2b2117` (100% of letterforms). Depth = 1.
- Signature: a single centered column whose measure widens from the 14px name to the 58ch vocabulary and then collapses onto `No tickets in this view.` at 74px — identity at minimum size, absence at maximum.
- Invariants: one ink; centered single column; the 74px gap sentence as the page's largest element; Palatino stack; the widening-then-collapsing measure rhythm.
- Assumptions & risks: a large centered serif line on a warm ground risks reading as a familiar editorial/luxury pose — the 14px tracked name and the tracked uppercase state run are what keep it operational; the gap sentence must never be given a second color.
- Round 2: keep the measure rhythm and single ink; the gap sentence stays text, never a banner, card, or colored notice.
