# OCR evaluation: photographed two-column physics textbook pages

## Scope

Three user-supplied photographed English textbook pages were evaluated locally. The source images are not committed to this public repository. They were 818–869 px wide, contained two columns, page curvature, uneven lighting and reverse-side show-through.

For each page, a visible prose passage was manually transcribed and used as a small reference sample. The samples contained 57, 105 and 74 words. Word error rate (WER) is therefore diagnostic rather than a whole-book accuracy claim.

## Result

| Page | Previous pipeline WER | Updated pipeline WER |
| --- | ---: | ---: |
| 1 | 66.7% | 8.8% |
| 2 | 56.2% | 1.0% |
| 3 | 63.5% | 4.1% |

The updated run used English-only recognition, raw-image preprocessing, automatic two-column detection and PSM 6 for detected columns. It also eliminated unexpected Hangul tokens and TSV control-character corruption.

Optional 1600 px upscaling improved page 1's sample WER to 3.5%, but worsened page 2 to 5.7%. Upscaling is therefore available through `--upscale-width` but remains disabled by default.

## Findings

- English-only recognition substantially reduces false characters on English books.
- Unconditional median filtering and global Otsu binarization can destroy thin serif strokes, punctuation and superscripts. Raw input is the safer default.
- Automatic column splitting improves reading order and lets Tesseract use a column-oriented segmentation mode.
- Low-resolution messenger-compressed images should produce a warning; camera originals are preferred.
- Tesseract does not recover mathematical structure reliably. Fractions, equation numbers, Greek letters, superscripts and scientific-notation exponents still require a dedicated formula-to-LaTeX engine and human review.
- Text physically cropped outside the photograph cannot be recovered by OCR.

## Regression coverage

Unit tests cover unmatched quotes in Tesseract TSV, preprocessing modes, optional upscaling, synthetic two-column detection, page output and manifest quality warnings. A future benchmark should use redistributable page fixtures with complete ground-truth text and formula annotations.
