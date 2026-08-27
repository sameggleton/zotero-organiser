import { describe, it, expect } from 'vitest';
import { decide } from '../src/core/policy.js';

describe('Policy', () => {
  it('correctly partitions scores into accepted, held, and ignored', () => {
    const scores = {
      'topic/history': 0.92,
      'method/computational': 0.74,
      'role/dataset': 0.45,
    };

    const decision = decide(scores, {
      autoThreshold: 0.85,
      triageThreshold: 0.65,
    });

    expect(decision.accepted).toEqual(new Set(['topic/history']));
    expect(decision.held).toEqual(new Set(['method/computational']));
    expect(decision.ignored).toEqual(new Set(['role/dataset']));
  });

  it('ignores suppressed tags regardless of score', () => {
    const scores = {
      'topic/history': 0.99,
      'method/computational': 0.75,
    };

    const decision = decide(scores, {
      autoThreshold: 0.85,
      triageThreshold: 0.65,
      suppressed: new Set(['topic/history']),
    });

    expect(decision.accepted.has('topic/history')).toBe(false);
    expect(decision.ignored.has('topic/history')).toBe(true);
    expect(decision.held).toEqual(new Set(['method/computational']));
  });
});
