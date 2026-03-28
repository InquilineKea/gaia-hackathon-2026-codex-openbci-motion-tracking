# ClawInstitute Proposal: Remote Music Neurofeedback Session Report

Date: 2026-03-28
Timezone: America/New_York
Project owner: Simfish
Primary stack: OpenBCI Cyton, Python real-time analyzers, Cloudflare Worker + D1, Spotify desktop logging, webcam event and eye tracking

## Executive Summary

On March 28, 2026 we built and tested a live music-neurofeedback stack that can:

- stream OpenBCI Cyton EEG in real time from Python
- compute peak alpha frequency (PAF), alpha/theta ratio, gamma/delta ratio, and 1/f falloff continuously
- detect artifact-heavy windows and warn when signal quality declines
- publish the live stream online through Cloudflare
- archive spectrum snapshots to D1 every 120 seconds
- log Spotify track changes and align them to before/after EEG response windows
- generate labeled screenshots for track-switch events
- tag coarse webcam events, approximate montage placement, and coarse eye state
- add experimental annotations such as nicotine dose and prior-night sleep

The system now supports a public remote-viewer workflow: other people can watch the live dashboard, inspect archived spectra, and review music-change screenshots. The next logical step is to add a collaborative suggestion queue so remote observers can recommend track changes in real time and the system can score outcomes.

## Public URLs

- Live dashboard: https://openbci-status-worker.simfish-openbci-live.workers.dev/
- Live spectrum page: https://openbci-status-worker.simfish-openbci-live.workers.dev/spectrum
- Live JSON: https://openbci-status-worker.simfish-openbci-live.workers.dev/live.json
- Live text status: https://openbci-status-worker.simfish-openbci-live.workers.dev/status.txt
- Spectrum archive feed: https://openbci-status-worker.simfish-openbci-live.workers.dev/spectra.json?limit=12
- Proposal markdown: https://openbci-status-worker.simfish-openbci-live.workers.dev/proposal/clawinstitute-music-neurofeedback-proposal-2026-03-28.md

## Public Code

- Curated repo: https://github.com/InquilineKea/openbci-motion-tracking-2026-03-28
- Workspace snapshot repo: https://github.com/InquilineKea/gaia-hackathon-2026-codex-openbci-motion-tracking/tree/codex/openbci-motion-tracking

## What We Built

### 1. Real-time EEG analyzer for OpenBCI Cyton

We moved from an unsuccessful NextSense Smartbuds attempt to a direct OpenBCI Cyton serial parser and analyzer. The resulting Python tools provide:

- rolling EEG traces
- live PSD
- PAF
- alpha/theta
- gamma/delta
- 1/f slope and r2
- artifact flags
- live text status and JSON payloads

Representative clean summary:

- median PAF: 9.50 Hz
- median alpha/theta: 0.19
- median gamma/delta: 0.0179
- median 1/f slope: -2.19
- median 1/f r2: 0.76
- overall quality: excellent

Source artifact:
- `/Users/simfish/Documents/GitHub/gaia-hackathon-2026/openbci_live_summary.txt`

### 2. Public Cloudflare live stream

We created a Cloudflare Worker plus D1 archive to publish:

- live rolling EEG payloads
- text status
- archived snapshot history
- archived spectrum snapshots
- a dedicated spectrum page

The spectrum page now shows the Spotify song aligned with each live or archived timestamp at the top of the chart.

### 3. Spotify-to-EEG event monitor

We added a Spotify logger and a track-change monitor that:

- detects track transitions
- measures baseline and response windows around each switch
- labels screenshots with the new soundtrack name
- records pre/post EEG averages
- includes eye-state labels when available
- plays an alert sound if electrode quality degrades for too long

### 4. Webcam event and eye tracking

We added webcam tools for:

- coarse hand and held-object tagging
- coarse nicotine-lozenge-to-mouth candidate tagging
- approximate electrode overlay labels on the head
- coarse eye state and gaze direction
- fixation metrics and eyes-closed events

These are deliberately heuristic and not presented as high-precision CV models.

### 5. Session annotations

We added structured experiment notes for factors that could influence EEG:

- 8 mg nicotine lozenge
- previous-night sleep duration of 3 hours 57 minutes

Source artifact:
- `/Users/simfish/Documents/GitHub/gaia-hackathon-2026/experiment_annotations.jsonl`

## Timestamped Session Timeline

Where possible, these timestamps come directly from saved artifacts or filenames.

| Time (EDT) | Event |
| --- | --- |
| 12:44:30 | Clean OpenBCI Cyton serial summary captured with median PAF 9.50 Hz and excellent overall quality. |
| 13:23:44 | Automated eyes-closed comparison summary saved; closed-eyes window contained 60 clean snapshots but the recent baseline archive window was empty, so automated comparative stats were unavailable in that later rerun. |
| 13:43:28 | Webcam eye fixation summary saved: center occupancy 0.757, saccade rate 1.91 Hz, mean gaze near center. |
| 14:06:55 | Initial OpenBCI motion-tracking and online streaming tools committed to Git. |
| 14:40:45 | Spotify logger recorded active playback: Miracle Tones, "4 Hz Theta Waves - Binaural Beats". |
| 14:57:53 | User-estimated nicotine event time for 8 mg lozenge. |
| 14:59:58 | First clean music-change event saved: 285 Hz Powerful Om Mantra Meditation -> 639 Hz Love Frequency. |
| 15:05:49 | Screenshot saved for "528 Hz Whole Body Regeneration". |
| 15:08:34 | Screenshot saved for "Solfeggio Frequencies 417 Hz". |
| 15:10:02 | Screenshot saved for "417 Hz Manifest Positive Energy". |
| 15:10:33 | Screenshot saved for "396 Hz Let Go of Fear Guilt". |
| 15:10:53 | Nicotine annotation recorded to JSONL. |
| 15:12:09 | Screenshot saved for "417 Hz Facilitate Change". |
| 15:12:47 | Sleep-duration annotation recorded to JSONL. |
| 15:14:10 | Screenshot saved for "528 Hz Fall Asleep". |
| 15:14:47 | Screenshot saved for "852 Hz Let Go of Overthinking Worries". |
| 15:17:18 | Screenshot saved for "3.2 Hz Healing Sleep Binaural Beats". |
| 15:19:16 | Screenshot saved for "777 Hz Manifest Positivity Self Confidence". |
| 15:21:09 | Screenshot saved for "Shiva's Meditation". |
| 15:21:23 | Spectrum archive row confirmed with Spotify metadata attached. |
| 15:23:42 | Screenshot saved for "Serene Waters". |
| 15:24:12 | Screenshot saved for "396 Hz Binaural Sleep No Fade Loopable". |
| 15:24:46 | Screenshot saved for "Sleep". |

## Key Quantitative Observations

### Baseline real-time EEG looked biologically plausible

The clean OpenBCI run produced:

- PAF around 8.4 to 11.3 Hz depending on window
- gamma much smaller than delta during clean periods
- 1/f slopes between about -1.4 and -2.2 during better-quality windows

This is much more realistic than the earlier OpenBCI GUI view that seemed to show gamma dominating delta.

### Example music-switch response: 285 Hz -> 639 Hz

At 14:59:58 EDT:

- PAF changed from 9.714 to 9.181 Hz
- alpha/theta changed from 0.603 to 0.409
- gamma/delta changed from 0.730 to 0.157
- 1/f slope changed from -0.675 to -1.388
- 1/f r2 changed from 0.484 to 0.678
- artifact rate changed from 1.00 to 0.48

Interpretation:
The post-switch window looked cleaner and more physiologic than the pre-switch baseline. The main effect was not a simple alpha increase. It was a reduction in broadband/noisy high-frequency contamination, producing a steeper and better-fit 1/f profile.

### Example music-switch response: 432 Hz -> 639 Hz

Earlier in the session:

- PAF rose from 8.875 to 10.013 Hz
- alpha/theta rose from 0.402 to 0.500
- gamma/delta fell from 0.725 to 0.669
- 1/f slope steepened from -0.863 to -1.241
- 1/f r2 improved from 0.503 to 0.592
- artifact rate fell from 1.00 to 0.59

Interpretation:
This switch looked cleaner after the change and is a candidate example of music-conditioned EEG improvement, though still not artifact-free.

### Eye tracking

The short fixation run yielded:

- center occupancy: 0.757
- peripheral occupancy: 0.243
- fixation episode count: 23
- saccade rate: 1.908 Hz

This gives a starting point for conditioning future music-response analyses on gaze stability and eye closure.

## Sample Figures

### Figure 1. Side-by-side EEG response around a 639 Hz track switch

![639 Hz side-by-side](https://openbci-status-worker.simfish-openbci-live.workers.dev/proposal/images/spotify-639hz-side-by-side.png)

### Figure 2. EEG response summary for 639 Hz Love Frequency

![639 Hz love frequency](https://openbci-status-worker.simfish-openbci-live.workers.dev/proposal/images/spotify-639hz-love-frequency.png)

### Figure 3. EEG response summary for 777 Hz Manifest Positivity Self Confidence

![777 Hz positivity](https://openbci-status-worker.simfish-openbci-live.workers.dev/proposal/images/spotify-777hz-manifest-positivity-self-confidence.png)

## What Worked

- OpenBCI Cyton produced usable live EEG when accessed through a direct serial parser.
- The online Cloudflare dashboard and D1 archive worked in real time.
- Spotify changes could be aligned to EEG response windows and saved as labeled images.
- Eye state, fixation stability, and basic experiment annotations can now be joined to EEG runs.
- Remote collaborators can already inspect live and archived data from public URLs.

## What Did Not Fully Work

- NextSense Smartbuds live streaming was not reliable in this environment and did not yield a usable 30-second PAF run.
- Webcam montage labeling is approximate and not a calibrated electrode-localization system.
- Webcam object and lozenge detection are heuristics, not trained classifiers.
- Some Spotify response windows were dominated by artifact, so any "frequency effect" claim needs stronger controls.

## ClawInstitute Proposal Summary

Title:
Collaborative Music Neurofeedback with Remote Observers, Live EEG, and Track-Switch Event Labeling

One-paragraph summary:
We built a live neurofeedback prototype that streams OpenBCI Cyton EEG online, computes PAF, alpha/theta, gamma/delta, and 1/f falloff continuously, aligns Spotify track switches to before/after neural response windows, and generates labeled visual evidence for each event. Remote collaborators can already inspect live and archived spectra through Cloudflare. The next phase is to let outside observers suggest or vote on track changes in real time while the system scores their impact on signal quality and targeted neural markers.

Core claim:
The interesting near-term opportunity is not merely "play binaural beats and look at a PSD." It is building a collaborative closed-loop experiment platform where music changes, state labels, annotations, and EEG outcomes are all timestamped and reviewable by remote participants.

## How To Make This Better

### Better experimental rigor

- add explicit eyes-open versus eyes-closed baseline blocks before every music run
- require minimum clean-signal thresholds before accepting a trial
- add per-channel contact quality proxies and suppression of bad channels
- normalize responses to a recent clean baseline rather than arbitrary preceding windows
- stratify analyses by nicotine timing, sleep deprivation, and gaze stability

### Better music-response modeling

- automatically extract track metadata and spectral features, not just frequency terms in titles
- compute response features beyond means: transient slope change, alpha peak sharpening, bandpower variance, recovery time
- score tracks by effect size after artifact rejection
- learn a personalized recommendation model over time

### Better remote collaboration

- add a public suggestion queue so observers can propose the next Spotify track
- add moderator approval or rate limiting to avoid spam
- show a live leaderboard of track suggestions and observed response scores
- allow collaborators to tag events such as "eyes closed," "movement," or "seemed calmer"
- expose an API endpoint for remote annotations with timestamps

### Better UI

- add a dedicated public experiment page that combines live spectrum, latest track, latest screenshot, and active annotations
- render eyes-open or eyes-closed state directly on the public dashboard
- let viewers scrub archived track switches and overlay PSDs by condition
- add embeddable iframes for the current stream and the recent-response gallery

## Suggested Next Experiments

1. Controlled A/B track testing with repeated alternating blocks and no movement.
2. Personalized track ranking using only clean windows with artifact rate below a strict threshold.
3. Remote crowd-sourced suggestion testing where collaborators vote on the next track and the system scores the response.
4. Closed-loop control where the system auto-selects the next track to maximize a target such as alpha/theta or minimize artifact while preserving a plausible 1/f slope.
5. Inclusion of physiological covariates such as sleep duration, nicotine timing, and eye closure state in the response model.

## Notes On Submission Status

This file is intentionally written as a submission-ready Markdown proposal for ClawInstitute. During this session, no public authenticated post-submission endpoint was discoverable from the unauthenticated site surface, so the safe deliverable is a hosted Markdown artifact plus embeddable figures and public URLs. If an authenticated ClawInstitute posting flow becomes available in-browser, this document is ready to paste as the proposal body.
