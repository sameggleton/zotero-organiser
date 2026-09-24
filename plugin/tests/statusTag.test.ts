import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { StateStore } from '../src/core/state.js';
import { StatusTagService } from '../src/events/statusTag.js';
import { OrganiserNotifier } from '../src/events/notifier.js';
import { ClassifierEngine } from '../src/classifier/engine.js';
import { parseTaxonomy } from '../src/core/taxonomy.js';
import { DEFAULT_TAXONOMY_YAML } from '../src/defaultTaxonomy.js';

const READING_ONLY_TAXONOMY = `schema_version: 1
version: "1.0.0"
classifier:
  semantic_namespaces: []
  workflow_namespaces:
    - status
namespaces:
  status:
    description: Reading state.
    kind: workflow
    classifier_eligible: false
    max_tags: 1
    values:
      reading:
        description: In progress.
`;

interface FakeItemOptions {
  key?: string;
  id?: number;
  tags?: string[];
  isRegular?: boolean;
  isFeed?: boolean;
}

function createFakeItem(options: FakeItemOptions = {}) {
  const item = {
    id: options.id,
    key: options.key || 'ITEM1',
    version: 1,
    isFeedItem: options.isFeed ?? false,
    savedTx: 0,
    addedTags: [] as string[],
    addedTypes: [] as Array<number | undefined>,
    isRegularItem: () => options.isRegular ?? true,
    getTags(): Array<{ tag: string; type?: number }> {
      return (options.tags || []).map((tag) => ({ tag, type: 0 }));
    },
    addTag(tag: string, type?: number) {
      item.addedTags.push(tag);
      item.addedTypes.push(type);
      (options.tags || (options.tags = [])).push(tag);
    },
    async saveTx() {
      item.savedTx += 1;
      return 1;
    },
  };
  return item;
}

function createService(stateStore: StateStore, overrides: Record<string, any> = {}) {
  return new StatusTagService(
    stateStore,
    {
      statusTagEnabled: true,
      statusTagName: 'status/to-read',
      writeEnabled: true,
      ...overrides,
    },
    parseTaxonomy(DEFAULT_TAXONOMY_YAML)
  );
}

describe('StatusTagService', () => {
  let stateStore: StateStore;
  let log: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    stateStore = new StateStore();
    log = vi.fn();
    vi.stubGlobal('Zotero', { log });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('applies the default status tag to a new item and tracks it', async () => {
    const service = createService(stateStore);
    const item = createFakeItem();

    const result = await service.applyToItem(item as any);

    expect(result).toBe('applied');
    expect(item.addedTags).toEqual(['status/to-read']);
    expect(item.addedTypes).toEqual([0]);
    expect(item.savedTx).toBe(1);

    const stored = await stateStore.getItem(item.key);
    expect(stored?.statusTag).toBe('status/to-read');
    expect(log).toHaveBeenCalled();
  });

  it('skips items that already carry any status/ namespaced tag', async () => {
    const service = createService(stateStore);
    const item = createFakeItem({ tags: ['status/reading'] });

    const result = await service.applyToItem(item as any);

    expect(result).toBe('skipped_existing_status');
    expect(item.addedTags).toEqual([]);
    expect(item.savedTx).toBe(0);
  });

  it('skips when disabled, when writes are off, or when the tag name is blank', async () => {
    const disabledService = createService(stateStore, { statusTagEnabled: false });
    const item = createFakeItem();
    expect(await disabledService.applyToItem(item as any)).toBe('skipped_disabled');
    expect(item.addedTags).toEqual([]);

    const gated = createService(stateStore, { writeEnabled: false });
    const gatedItem = createFakeItem({ key: 'GATED' });
    expect(await gated.applyToItem(gatedItem as any)).toBe('skipped_writes_disabled');
    expect(gatedItem.addedTags).toEqual([]);
    expect(await stateStore.getItem(gatedItem.key)).toBeNull();

    const blankService = createService(stateStore, { statusTagName: '   ' });
    const item2 = createFakeItem({ key: 'ITEM2' });
    expect(await blankService.applyToItem(item2 as any)).toBe('skipped_disabled');
    expect(item2.addedTags).toEqual([]);
  });

  it('rejects tags outside the taxonomy status namespace', async () => {
    const service = createService(stateStore, { statusTagName: 'priority/high' });
    const priorityItem = createFakeItem({ key: 'PRI' });
    expect(await service.applyToItem(priorityItem as any)).toBe('skipped_invalid_tag');
    expect(priorityItem.addedTags).toEqual([]);

    service.updateOptions({ statusTagName: 'topic/history' });
    const topicItem = createFakeItem({ key: 'TOP' });
    expect(await service.applyToItem(topicItem as any)).toBe('skipped_invalid_tag');
    expect(await stateStore.getItem(topicItem.key)).toBeNull();

    service.updateOptions({ statusTagName: 'status/reading' });
    const readingItem = createFakeItem({ key: 'READ' });
    expect(await service.applyToItem(readingItem as any)).toBe('applied');
    expect(readingItem.addedTags).toEqual(['status/reading']);
  });

  it('skips non-regular items and feed items', async () => {
    const service = createService(stateStore);
    const attachment = createFakeItem({ isRegular: false });
    expect(await service.applyToItem(attachment as any)).toBe('skipped_invalid_item');

    const feedItem = createFakeItem({ key: 'FEED1', isFeed: true });
    expect(await service.applyToItem(feedItem as any)).toBe('skipped_invalid_item');
  });

  it('does not re-apply when the tracked status tag is still on the item', async () => {
    const service = createService(stateStore);
    const item = createFakeItem();

    expect(await service.applyToItem(item as any)).toBe('applied');
    expect(await service.applyToItem(item as any)).toBe('skipped_already_tracked');
    expect(item.addedTags).toEqual(['status/to-read']);
  });

  it('suppresses a tracked status tag that disappeared without a delete event', async () => {
    const service = createService(stateStore);
    const item = createFakeItem();
    expect(await service.applyToItem(item as any)).toBe('applied');

    item.getTags = () => [];
    const result = await service.applyToItem(item as any);

    expect(result).toBe('skipped_suppressed');
    expect(item.addedTags).toEqual(['status/to-read']);
    const stored = await stateStore.getItem(item.key);
    expect(stored?.statusTag).toBeNull();
    expect(stored?.suppressedTags.has('status/to-read')).toBe(true);
  });

  it('does not record the status tag when the Zotero write does not succeed', async () => {
    const service = createService(stateStore);
    const unsaved = createFakeItem({ key: 'UNSAVED' });
    delete (unsaved as { saveTx?: unknown }).saveTx;

    expect(await service.applyToItem(unsaved as any)).toBe('skipped_write_failed');
    expect(unsaved.addedTags).toEqual([]);
    expect(await stateStore.getItem(unsaved.key)).toBeNull();

    const rolledBack = createFakeItem({ key: 'ROLLBACK' });
    rolledBack.saveTx = async () => false as unknown as number;
    expect(await service.applyToItem(rolledBack as any)).toBe('skipped_write_failed');
    expect(await stateStore.getItem(rolledBack.key)).toBeNull();
  });

  it('suppresses re-adding after the user removes the status tag', async () => {
    const service = createService(stateStore);
    const item = createFakeItem();

    await service.applyToItem(item as any);

    item.getTags = () => [];
    const stored = (await stateStore.getItem(item.key))!;
    const removed = await service.handleStatusTagRemoved(item as any, stored);
    expect(removed).toBe(true);

    const updated = await stateStore.getItem(item.key);
    expect(updated?.statusTag).toBeNull();
    expect(updated?.suppressedTags.has('status/to-read')).toBe(true);

    const result = await service.applyToItem(item as any);
    expect(result).toBe('skipped_suppressed');
    expect(item.addedTags).toEqual(['status/to-read']);
  });

  it('reports false when the removed tag was not the status tag', async () => {
    const service = createService(stateStore);
    const item = createFakeItem({ tags: ['topic/physics'] });

    const stored = {
      itemKey: item.key,
      zoteroVersion: 1,
      state: 'discovered' as const,
      autoTags: new Set<string>(),
      suppressedTags: new Set<string>(),
      triageTags: {},
      candidateTags: {},
      statusTag: null,
      retryCount: 0,
    };
    expect(await service.handleStatusTagRemoved(item as any, stored)).toBe(false);
  });
});

describe('OrganiserNotifier status tag wiring', () => {
  let timers: Map<number, () => Promise<void> | void>;
  let nextTimerId: number;
  let notifierItem: any;

  beforeEach(() => {
    timers = new Map();
    nextTimerId = 1;
    vi.stubGlobal('Zotero', {
      log: vi.fn(),
      Items: {
        get: (id: number) => (id === 1 ? notifierItem : false),
      },
    });
    vi.stubGlobal('window', {
      setTimeout: (fn: () => Promise<void> | void) => {
        const id = nextTimerId++;
        timers.set(id, fn);
        return id;
      },
      clearTimeout: (id: number) => {
        timers.delete(id);
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function flushSettled(): Promise<void> {
    const jobs = [...timers.values()];
    timers.clear();
    for (const job of jobs) {
      await job();
    }
  }

  function createNotifier(stateStore: StateStore, overrides: Record<string, any> = {}) {
    const taxonomy = parseTaxonomy(DEFAULT_TAXONOMY_YAML);
    const classifier = new ClassifierEngine(taxonomy, {
      mode: 'local',
      autoAcceptThreshold: 0.85,
      triageThreshold: 0.65,
    });
    return new OrganiserNotifier(stateStore, classifier, taxonomy, {
      writeEnabled: true,
      onlyNewItems: true,
      allowTagRemoval: false,
      autoThreshold: 0.85,
      triageThreshold: 0.65,
      settleMs: 3000,
      statusTagEnabled: true,
      statusTagName: 'status/to-read',
      ...overrides,
    });
  }

  it('applies the status tag after settle on add, and not on modify', async () => {
    const stateStore = new StateStore();
    const notifier = createNotifier(stateStore);
    notifierItem = createFakeItem({ id: 1 });

    await (notifier as any).handleNotification('add', 'item', [1], {});
    expect(notifierItem.addedTags).toEqual([]);

    await flushSettled();
    expect(notifierItem.addedTags).toEqual(['status/to-read']);
    const stored = await stateStore.getItem(notifierItem.key);
    expect(stored?.statusTag).toBe('status/to-read');

    notifierItem = createFakeItem({ key: 'ITEM2', id: 1, tags: ['status/reading'] });
    await (notifier as any).handleNotification('add', 'item', [1], {});
    await flushSettled();
    expect(notifierItem.addedTags).toEqual([]);

    notifierItem = createFakeItem({ key: 'ITEM3', id: 1 });
    await (notifier as any).handleNotification('modify', 'item', [1], {});
    await flushSettled();
    expect(notifierItem.addedTags).toEqual([]);
  });

  it('sees status tags that arrive during the settle delay', async () => {
    const stateStore = new StateStore();
    const notifier = createNotifier(stateStore);
    const stale = createFakeItem({ key: 'STALE', id: 1 });
    const fresh = createFakeItem({ key: 'FRESH', id: 1, tags: ['status/reading'] });
    notifierItem = stale;

    await (notifier as any).handleNotification('add', 'item', [1], {});
    notifierItem = fresh;
    await flushSettled();

    expect(stale.addedTags).toEqual([]);
    expect(fresh.addedTags).toEqual([]);
    expect((await stateStore.getItem('FRESH'))?.statusTag ?? null).toBeNull();
    expect(await stateStore.getItem('STALE')).toBeNull();
  });

  it('updateOptions propagates status tag settings and the write gate', async () => {
    const stateStore = new StateStore();
    const notifier = createNotifier(stateStore);

    notifier.updateOptions({ statusTagEnabled: false, statusTagName: 'workflow/new' });

    notifierItem = createFakeItem({ key: 'ITEM9', id: 1 });
    await (notifier as any).handleNotification('add', 'item', [1], {});
    await flushSettled();
    expect(notifierItem.addedTags).toEqual([]);

    notifier.updateOptions({ statusTagEnabled: true, statusTagName: 'status/to-read', writeEnabled: false });
    notifierItem = createFakeItem({ key: 'ITEM10', id: 1 });
    await (notifier as any).handleNotification('add', 'item', [1], {});
    await flushSettled();
    expect(notifierItem.addedTags).toEqual([]);
    expect((await stateStore.getItem('ITEM10'))?.statusTag ?? null).toBeNull();
  });

  it('drops a configured tag the active taxonomy no longer defines', async () => {
    const stateStore = new StateStore();
    const notifier = createNotifier(stateStore);
    notifier.updateTaxonomy(parseTaxonomy(READING_ONLY_TAXONOMY));

    notifierItem = createFakeItem({ id: 1 });
    await (notifier as any).handleNotification('add', 'item', [1], {});
    await flushSettled();

    expect(notifierItem.addedTags).toEqual([]);
    expect((await stateStore.getItem(notifierItem.key))?.statusTag ?? null).toBeNull();
  });

  it('marks the status tag suppressed (no exemplar) when removed by the user', async () => {
    const stateStore = new StateStore();
    const notifier = createNotifier(stateStore);
    notifierItem = createFakeItem({ id: 1 });

    await (notifier as any).handleNotification('add', 'item', [1], {});
    await flushSettled();
    expect(notifierItem.addedTags).toEqual(['status/to-read']);

    notifierItem.getTags = () => [];
    await (notifier as any).handleNotification('delete', 'item-tag', [1], {});

    const stored = await stateStore.getItem(notifierItem.key);
    expect(stored?.statusTag).toBeNull();
    expect(stored?.suppressedTags.has('status/to-read')).toBe(true);

    await (notifier as any).handleNotification('add', 'item', [1], {});
    await flushSettled();
    expect(notifierItem.addedTags).toEqual(['status/to-read']);
  });
});
