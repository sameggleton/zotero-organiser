export interface Decision {
  accepted: Set<string>;
  held: Set<string>;
  ignored: Set<string>;
}

export interface DecideOptions {
  autoThreshold: number;
  triageThreshold: number;
  suppressed?: Set<string>;
}

export function decide(
  scores: Record<string, number>,
  options: DecideOptions
): Decision {
  const { autoThreshold, triageThreshold, suppressed = new Set<string>() } = options;
  const accepted = new Set<string>();
  const held = new Set<string>();
  const ignored = new Set<string>();

  for (const [tag, confidence] of Object.entries(scores)) {
    if (suppressed.has(tag) || confidence < triageThreshold) {
      ignored.add(tag);
    } else if (confidence >= autoThreshold) {
      accepted.add(tag);
    } else {
      held.add(tag);
    }
  }

  return { accepted, held, ignored };
}
