# Implementation plan for issue #1

Tests are intentionally kept local and are ignored by version control. Ticks mark implemented work; independent AcqKnowledge validation remains pending.

Issue #1 uses **`run_preprocessing.py`** and **`run_analysis.py`**, with **`--preview_for_participant`** for inspection, replacing `preprocessing_charts.py`. Extend previews with every signal-processing step, retaining a **superimposed view of the original signal and every intermediate result**. Use distinct colours and line styles, settings in legends, and exact recording time in minutes. Process the complete recording continuously; ignore **Change Selected Area**. Save overview and display-only zoom PNGs under `OUTPUT_DIR` and support interactive zoom/pan. The researcher reviews charts before proceeding to the next step.

Keep processing choices in `config.yaml` under `PREPROCESSING` and `ANALYSIS`, with display settings under `PREPROCESSING_CHARTS` and `ANALYSIS_CHARTS`. Smoothing widths use samples at the processed rate; the phasic baseline window uses seconds. Runners load configuration and save outputs; reusable helpers receive parameters.

The four supplied `.acq` files contain raw channels only. Their Excel files provide final summaries, but no filtered/phasic waveforms or SCR event tables. Independent waveform and detection validation requires those exports.

The two physiological processing modules are:

| Module | Responsibility |
|---|---|
| `src/preprocessing/signal_preprocessing.py` | Resampling, smoothing, FIR filtering, intermediate signals, and processed recordings |
| `src/preprocessing/signal_analysis.py` | Phasic derivation and SCR detection; stimulus matching and summaries remain planned |

Both expose ordinary functions accepting signals, sampling rates, and parameters. File discovery, configuration, participant loops, and saving remain in the runners. Plotting helpers in `src/common/signal_plot_utils.py` return figures.

1. [x] **`feat: implement resampling and smoothing`**

   Validate finite numeric Series with contiguous integer sample indices. Use **linear resampling from 2000 to 1000 Hz**, without a preceding anti-alias filter. Anchor the output grid at the first input sample and include only positions at or before the last sample: `floor((N - 1) * target_fs / fs) + 1`.

   Use a **centered 100-sample median**, covering positions `i - 50` through `i + 49`. Average the central pair for even medians and shrink windows at edges.

   Local synthetic tests cover sample grids, nonzero origins, even windows, spikes, constants, and odd-length inputs. NumPy/SciPy are direct dependencies with an updated lockfile. Shared overlays retain exact recording-time alignment.

   **Acceptance:** the implementation and focused tests exist; AcqKnowledge grid, median, and edge agreement remain unverified.

2. [x] **`feat: implement FIR filtering and expose preprocessing graphs`**

   The complete sequence is:

   ```text
   raw EDA → resampling → smoothing → FIR filtering
   ```

   Use a **1 Hz Hamming lowpass**, unity gain, compensated delay, and reflected edges. The optimized estimate is `ceil(4 * fs / cutoff_hz)`, increased to odd: **4001 coefficients at 1000 Hz**. Fixed odd counts remain configurable. Apply one FIR pass without substituting NeuroKit's default cleaning.

   Return all intermediate signals, exact timelines, and metadata. `plot_preprocessing(...)` provides linked panels, raw/filtered comparisons, and optional reference/difference traces.

   `run_preprocessing.py` reads segmented recordings and saves filtered EDA with trigger labels and other channels as `PREPROCESSED_DIR/clean_<participant_id>.parquet`. Other columns use the original sample at or immediately before each output position. Both runners respect `ignore_participants` and `no_eda`.

   **Acceptance:** preprocessing, overlays, linked panels, and overview/zoom PNG exports are implemented; independent waveform agreement and researcher review remain pending.

3. [x] **`feat: implement phasic derivation and SCR detection`**

   Subtract a **centered 5-second moving median baseline**, with shrinking edges, retaining negative phasic values. Treat the method and window units as calibration choices.

   Start an SCR strictly above **0.01 µS** and end it at the first return to zero or below. Allow one response per positive excursion. Reject complete candidates strictly below **10% of the largest complete candidate's phasic maximum**; accept equality. Retain incomplete responses as rejected with explicit reasons and a missing end where unobserved.

   Report onset, peak, end, amplitude, phasic maximum, status, and rejection reason. Amplitude is the filtered EDA maximum within the inclusive onset/end interval minus filtered EDA at onset. Tests cover equality, recrossings, incomplete boundaries, and empty/flat signals.

   `run_analysis.py` reads saved filtered EDA and writes `OUTPUT_DIR/analysis/scr_<participant_id>.csv`; baseline/phasic waveforms remain in memory. Previews overlay these with earlier steps reconstructed from segmented input using current settings, clearly labelled separately from the saved analysis input.

   **Acceptance:** detection accepts independent filtered/phasic input; overlays and `plot_analysis(...)` event panels exist. Independent calibration and runner export of event panels remain pending.

4. [ ] **`feat: reproduce stimulus matching`**

   Accept a stimulus table with event positions and labels; keep raw-pin decoding in segmentation/reference helpers.

   Implement AcqKnowledge's matching window, event ordering, and response-reuse rules. Test overlapping windows, multiple candidates, unmatched stimuli, and responses outside the window. Preserve exact timing across sampling grids.

   Extend analysis previews with stimulus markers and response associations on the shared recording timeline, retaining earlier overlays and clear legends.

   **Acceptance:** synthetic matches are established, reference stimulus totals agree, and exported charts make associations inspectable.

5. [ ] **`feat: reproduce analysis summaries and diagnostic graphs`**

   Produce the supplied Excel columns:

   ```text
   Amplitude, Magnitude, Matched, Non-matched, Total, Freq%, Label
   ```

   Reproduce row-inclusion rules, including labels present in recordings but absent from summaries, particularly for participant 221.

   - [x] Provide `plot_analysis(...)` with linked filtered/phasic panels, SCR onset/peak/end markers, and rejection decisions.
   - [ ] Add stimulus markers and associations, and export these panels from `run_analysis.py` alongside the complete signal overlay.

   **Acceptance:** summary formulas and empty results pass focused tests; each detected and matched response is inspectable in exported charts.

6. [ ] **`test: verify reuse on recording segments`**

   - [x] Preserve same-rate indices and explicit recording-time mappings after resampling, including nonzero origins.
   - [x] Cover short/empty signals, unequal grids, legends, and display-only zooms in local tests.
   - [x] Expose `reference_max_us` for recording-wide rejection when analyzing a segment; otherwise use complete candidates in the supplied span.
   - [ ] Extend segment checks to stimulus matching, summaries, and empty stimulus tables.

   Filtering a trial independently can differ from slicing continuously filtered data. Keep boundary context and rejection scope explicit.

   **Acceptance:** the complete analysis APIs support participant and segment inputs without participant-specific assumptions.

7. [ ] **`test: enforce four-participant parity and document module usage`**

   Compare every exported Excel value across all four recordings. Expected matched totals are:

   | Participant | Matched responses |
   |---|---:|
   | 128 | 118 |
   | 149 | 181 |
   | 207 | 196 |
   | 221 | 52 |

   Require exact labels, counts, and matching decisions, with justified fixed tolerances for floating-point measurements and waveforms, including endpoints.

   - [x] Document current runners, parameters, outputs, and previews in the README.
   - [x] Separate synthetic `unittest` checks from explicitly enabled local reference tests.
   - [ ] Complete module examples, four-participant comparisons, independent waveform checks, and overview/zoom exports with researcher review.

   **Acceptance:** all reference comparisons pass and all processing stages are visually inspectable. Participant runners are already part of issue #1; trial-specific orchestration remains for issue #2.

**Final-summary agreement** and **independent preprocessing agreement** remain separate acceptance checks. Excel agreement alone cannot establish waveform parity. Per-step charts and researcher review continue to apply to later extensions of both runners.
