import { describe, it, expect } from 'vitest';
import { reconcile } from '../src/core/reconcile.js';

describe('Reconcile', () => {
  it('preserves existing human manual tags and adds new accepted auto tags', () => {
    const current = new Set(['my-manual-tag', 'status/reading']);
    const previousAuto = new Set<string>();
    const accepted = new Set(['topic/history']);

    const res = reconcile(current, previousAuto, accepted);

    expect(res.tags).toEqual(new Set(['my-manual-tag', 'status/reading', 'topic/history']));
    expect(res.autoTags).toEqual(new Set(['topic/history']));
    expect(res.suppressedTags).toEqual(new Set());
  });

  it('detects user deletion of a previously-owned auto tag and marks it suppressed', () => {
    // Organiser previously added 'topic/history', but user deleted it from Zotero
    const current = new Set(['my-manual-tag']);
    const previousAuto = new Set(['topic/history']);
    const accepted = new Set(['topic/history', 'method/computational']);

    const res = reconcile(current, previousAuto, accepted);

    // 'topic/history' should NOT be re-added; it is suppressed
    expect(res.tags).toEqual(new Set(['my-manual-tag', 'method/computational']));
    expect(res.autoTags).toEqual(new Set(['method/computational']));
    expect(res.suppressedTags).toEqual(new Set(['topic/history']));
  });

  it('never mutates or claims status/* or priority/* tags', () => {
    const current = new Set(['status/reading', 'priority/high']);
    const previousAuto = new Set(['status/to-read']); // Old state anomaly
    const accepted = new Set(['status/read', 'priority/core', 'topic/history']);

    const res = reconcile(current, previousAuto, accepted);

    // Only topic/history should be added; status and priority should remain unchanged as in current
    expect(res.tags).toEqual(new Set(['status/reading', 'priority/high', 'topic/history']));
    expect(res.autoTags).toEqual(new Set(['topic/history']));
  });

  it('preserves retained auto tags when allowTagRemoval is false', () => {
    const current = new Set(['topic/history', 'role/review']);
    const previousAuto = new Set(['topic/history', 'role/review']);
    // New classifier run only accepted topic/history, not role/review
    const accepted = new Set(['topic/history']);

    const resWithNoRemoval = reconcile(current, previousAuto, accepted, {
      allowTagRemoval: false,
    });

    expect(resWithNoRemoval.tags).toEqual(new Set(['topic/history', 'role/review']));

    const resWithRemoval = reconcile(current, previousAuto, accepted, {
      allowTagRemoval: true,
    });

    expect(resWithRemoval.tags).toEqual(new Set(['topic/history']));
  });
});
