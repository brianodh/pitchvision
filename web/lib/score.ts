// Scores are raw model outputs at a detection peak, not calibrated probabilities (README_v8: "Output scores
// are raw model outputs, not calibrated probabilities. The 0.5 default threshold was not tuned"). The UI
// therefore only ever shows a *relative* bar between the threshold and 1 — never a percentage.

export function relativeScore(score: number, threshold: number): number {
  const span = Math.max(1e-6, 1 - threshold);
  return Math.min(1, Math.max(0.04, (score - threshold) / span));
}

export const SCORE_EXPLAINER =
  "Relative model score between the detection threshold and the maximum. It ranks detections against each other; it is not a probability that the event is real.";
