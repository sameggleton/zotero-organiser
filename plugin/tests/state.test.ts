import { describe, expect, it, beforeEach } from 'vitest';
import { StateStore, ItemRecord } from '../src/core/state.js';
import { PreferenceMemory } from '../src/classifier/preferenceMemory.js';

describe('StateStore (Tier 1 Exemplar Persistence & Preference Memory)', () => {
  let store: StateStore;
  let prefMem: PreferenceMemory;

  beforeEach(() => {
    prefMem = new PreferenceMemory();
    store = new StateStore(prefMem);
  });

  it('saves and loads exemplars in memory mode', async () => {
    const vector = [0.1, 0.2, 0.3];
    await store.saveExemplar('ITEM1', 'topic/neural-nets', 'positive', vector);

    const exemplars = await store.loadAllExemplars();
    expect(exemplars.length).toBe(1);
    expect(exemplars[0].itemKey).toBe('ITEM1');
    expect(exemplars[0].tag).toBe('topic/neural-nets');
    expect(exemplars[0].label).toBe('positive');
    expect(exemplars[0].vector).toEqual(vector);
  });

  it('removes exemplars correctly', async () => {
    await store.saveExemplar('ITEM1', 'topic/nlp', 'positive', [1, 0]);
    await store.saveExemplar('ITEM2', 'topic/nlp', 'negative', [0, 1]);

    expect((await store.loadAllExemplars()).length).toBe(2);

    await store.removeExemplar('ITEM1', 'topic/nlp', 'positive');
    const remaining = await store.loadAllExemplars();
    expect(remaining.length).toBe(1);
    expect(remaining[0].itemKey).toBe('ITEM2');
    expect(remaining[0].label).toBe('negative');

    await store.removeExemplar('ITEM2', 'topic/nlp');
    expect((await store.loadAllExemplars()).length).toBe(0);
  });

  it('overwrites opposite label when saving exemplar for same itemKey and tag', async () => {
    await store.saveExemplar('ITEM1', 'topic/nlp', 'negative', [0, 1]);
    expect((await store.loadAllExemplars())[0].label).toBe('negative');

    await store.saveExemplar('ITEM1', 'topic/nlp', 'positive', [1, 0]);
    const list = await store.loadAllExemplars();
    expect(list.length).toBe(1);
    expect(list[0].label).toBe('positive');
    expect(list[0].vector).toEqual([1, 0]);
  });

  it('wires acceptTriageTag to positive exemplar storage and PreferenceMemory', async () => {
    const record: ItemRecord = {
      itemKey: 'ITEM1',
      zoteroVersion: 1,
      state: 'needs_triage',
      autoTags: new Set<string>(),
      suppressedTags: new Set<string>(),
      triageTags: { 'topic/machine-learning': 0.78 },
      candidateTags: {},
      retryCount: 0,
    };
    await store.saveItem(record);

    const fakeItem = {
      key: 'ITEM1',
      title: 'Machine Learning Fundamentals',
      tags: [],
    };

    const docVec = [0.8, 0.6];
    const updated = await store.acceptTriageTag(fakeItem, 'topic/machine-learning', {
      score: 0.78,
      vector: docVec,
    });

    expect(updated).not.toBeNull();
    expect(updated!.autoTags.has('topic/machine-learning')).toBe(true);
    expect(updated!.triageTags['topic/machine-learning']).toBeUndefined();
    expect(updated!.state).toBe('organised');

    // Exemplar saved in store
    const exemplars = await store.loadAllExemplars();
    expect(exemplars.length).toBe(1);
    expect(exemplars[0].tag).toBe('topic/machine-learning');
    expect(exemplars[0].label).toBe('positive');

    // Updated in PreferenceMemory
    const stats = prefMem.getStats();
    expect(stats.positiveCount).toBe(1);
    expect(stats.negativeCount).toBe(0);
  });

  it('wires rejectTriageTag to negative exemplar storage and PreferenceMemory', async () => {
    const record: ItemRecord = {
      itemKey: 'ITEM2',
      zoteroVersion: 1,
      state: 'needs_triage',
      autoTags: new Set<string>(),
      suppressedTags: new Set<string>(),
      triageTags: { 'topic/nlp': 0.72 },
      candidateTags: {},
      retryCount: 0,
    };
    await store.saveItem(record);

    const docVec = [0.1, 0.9];
    const updated = await store.rejectTriageTag('ITEM2', 'topic/nlp', {
      score: 0.72,
      vector: docVec,
    });

    expect(updated).not.toBeNull();
    expect(updated!.suppressedTags.has('topic/nlp')).toBe(true);
    expect(updated!.triageTags['topic/nlp']).toBeUndefined();
    expect(updated!.state).toBe('no_matches');

    const exemplars = await store.loadAllExemplars();
    expect(exemplars.length).toBe(1);
    expect(exemplars[0].tag).toBe('topic/nlp');
    expect(exemplars[0].label).toBe('negative');

    const stats = prefMem.getStats();
    expect(stats.negativeCount).toBe(1);
    expect(stats.positiveCount).toBe(0);
  });

  it('wires addCustomTaxonomyTag to positive exemplar and clears previous suppression', async () => {
    const record: ItemRecord = {
      itemKey: 'ITEM3',
      zoteroVersion: 1,
      state: 'no_matches',
      autoTags: new Set<string>(),
      suppressedTags: new Set<string>(['topic/robotics']),
      triageTags: {},
      candidateTags: {},
      retryCount: 0,
    };
    await store.saveItem(record);

    const fakeItem = { key: 'ITEM3', title: 'Robotics Control Systems' };
    const docVec = [0.5, 0.5];

    await store.addCustomTaxonomyTag(fakeItem, 'topic/robotics', 'v1.0.0', docVec);

    const updated = await store.getItem('ITEM3');
    expect(updated!.autoTags.has('topic/robotics')).toBe(true);
    expect(updated!.suppressedTags.has('topic/robotics')).toBe(false);

    const exemplars = await store.loadAllExemplars();
    expect(exemplars.length).toBe(1);
    expect(exemplars[0].label).toBe('positive');

    expect(prefMem.getStats().positiveCount).toBe(1);
    expect(prefMem.getStats().negativeCount).toBe(0);
  });

  it('wires removeAutoTag to negative exemplar and suppression', async () => {
    const record: ItemRecord = {
      itemKey: 'ITEM4',
      zoteroVersion: 1,
      state: 'organised',
      autoTags: new Set<string>(['topic/ai']),
      suppressedTags: new Set<string>(),
      triageTags: {},
      candidateTags: {},
      retryCount: 0,
    };
    await store.saveItem(record);

    const fakeItem = { key: 'ITEM4', title: 'Artificial Intelligence Review' };
    const docVec = [0.2, 0.8];

    await store.removeAutoTag(fakeItem, 'topic/ai', docVec);

    const updated = await store.getItem('ITEM4');
    expect(updated!.autoTags.has('topic/ai')).toBe(false);
    expect(updated!.suppressedTags.has('topic/ai')).toBe(true);

    const exemplars = await store.loadAllExemplars();
    expect(exemplars.length).toBe(1);
    expect(exemplars[0].label).toBe('negative');

    expect(prefMem.getStats().negativeCount).toBe(1);
  });

  it('wires unsuppressTag to negative exemplar removal in DB and PreferenceMemory', async () => {
    const record: ItemRecord = {
      itemKey: 'ITEM5',
      zoteroVersion: 1,
      state: 'no_matches',
      autoTags: new Set<string>(),
      suppressedTags: new Set<string>(['topic/nlp']),
      triageTags: {},
      candidateTags: {},
      retryCount: 0,
    };
    await store.saveItem(record);
    await store.saveExemplar('ITEM5', 'topic/nlp', 'negative', [0.1, 0.9]);
    prefMem.addExemplar({
      itemKey: 'ITEM5',
      tag: 'topic/nlp',
      label: 'negative',
      vector: [0.1, 0.9],
      timestamp: new Date().toISOString(),
    });

    expect(prefMem.getStats().negativeCount).toBe(1);

    await store.unsuppressTag('ITEM5', 'topic/nlp');

    const updated = await store.getItem('ITEM5');
    expect(updated!.suppressedTags.has('topic/nlp')).toBe(false);

    const exemplars = await store.loadAllExemplars();
    expect(exemplars.length).toBe(0);
    expect(prefMem.getStats().negativeCount).toBe(0);
  });

  it('executes SQL queries when a db connection is provided', async () => {
    const executedQueries: Array<{ sql: string; params: any[] }> = [];
    const mockDb = {
      execute: async (sql: string, params: any[] = []) => {
        executedQueries.push({ sql, params });
        if (sql.includes('SELECT item_key, tag, label')) {
          return [
            {
              item_key: 'SQL_ITEM',
              tag: 'topic/database',
              label: 'positive',
              vector_json: '[0.5, 0.5]',
              timestamp: '2026-08-27T00:00:00.000Z',
            },
          ];
        }
        return [];
      },
    };

    store.setDb(mockDb);

    await store.saveExemplar('SQL_ITEM', 'topic/database', 'positive', [0.5, 0.5]);
    expect(executedQueries.some((q) => q.sql.includes('INSERT INTO exemplars'))).toBe(true);

    const rows = await store.loadAllExemplars();
    expect(rows.length).toBe(1);
    expect(rows[0].itemKey).toBe('SQL_ITEM');
    expect(rows[0].tag).toBe('topic/database');
    expect(rows[0].vector).toEqual([0.5, 0.5]);

    await store.removeExemplar('SQL_ITEM', 'topic/database', 'positive');
    expect(executedQueries.some((q) => q.sql.includes('DELETE FROM exemplars'))).toBe(true);
  });
});
