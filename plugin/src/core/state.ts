import { Exemplar, PreferenceMemory } from '../classifier/preferenceMemory.js';
import { extractDocumentVector } from './document.js';

export interface ItemRecord {
  itemKey: string;
  zoteroVersion: number;
  state:
    | 'discovered'
    | 'waiting_for_attachment'
    | 'classifying'
    | 'needs_triage'
    | 'organised'
    | 'no_matches'
    | 'error';
  discoveredAt?: string;
  readyAt?: string;
  classifiedAt?: string;
  taxonomyVersion?: string;
  classifierVersion?: string;
  inputHash?: string;
  autoTags: Set<string>;
  suppressedTags: Set<string>;
  triageTags: Record<string, number>;
  candidateTags: Record<string, number>;
  lastError?: string;
  retryCount: number;
}

export interface InteractionEvent {
  eventId?: number;
  itemKey: string;
  inputHash?: string;
  tag: string;
  action: 'accepted' | 'rejected' | 'manual_added' | 'removed' | 'unsuppressed' | 'shown_no_action';
  score?: number;
  candidateRank?: number;
  displayedCandidates?: string[];
  denseScore?: number;
  lexicalScore?: number;
  nliScore?: number;
  classifierVersion?: string;
  taxonomyVersion?: string;
  timestamp?: string;
}

declare const ChromeUtils: any;
declare const PathUtils: any;

export class StateStore {
  private db: any = null;
  private preferenceMemory: PreferenceMemory | null = null;
  private memoryItems = new Map<string, ItemRecord>();
  private memoryExemplars: Exemplar[] = [];
  private memoryMeta = new Map<string, string>();
  private memoryEvents: InteractionEvent[] = [];

  constructor(preferenceMemory?: PreferenceMemory | null) {
    this.preferenceMemory = preferenceMemory || null;
  }

  public setPreferenceMemory(preferenceMemory: PreferenceMemory | null): void {
    this.preferenceMemory = preferenceMemory;
  }

  public getPreferenceMemory(): PreferenceMemory | null {
    return this.preferenceMemory;
  }

  public setDb(db: any): void {
    this.db = db;
  }

  async init(): Promise<void> {
    if (typeof Zotero === 'undefined') {
      return;
    }

    try {
      if (typeof ChromeUtils !== 'undefined' && typeof ChromeUtils.importESModule === 'function') {
        const { Sqlite } = ChromeUtils.importESModule('resource://gre/modules/Sqlite.sys.mjs');
        const dbPath = PathUtils.join(Zotero.DataDirectory.dir, 'zotero-organiser.sqlite');
        this.db = await Sqlite.openConnection({ path: dbPath });
      } else if (Zotero.DBConnection) {
        this.db = new Zotero.DBConnection('zotero-organiser');
      }
    } catch (e) {
      if (typeof Zotero.log === 'function') {
        Zotero.log(`[zotero-organiser] StateStore connection init note: ${e}`);
      }
    }

    if (!this.db) return;

    try {
      await this.query(`
        CREATE TABLE IF NOT EXISTS items (
          item_key TEXT PRIMARY KEY,
          zotero_version INTEGER NOT NULL,
          state TEXT NOT NULL,
          discovered_at TEXT,
          ready_at TEXT,
          classified_at TEXT,
          taxonomy_version TEXT,
          classifier_version TEXT,
          input_hash TEXT,
          auto_tags_json TEXT NOT NULL DEFAULT '[]',
          suppressed_tags_json TEXT NOT NULL DEFAULT '[]',
          triage_tags_json TEXT NOT NULL DEFAULT '{}',
          all_candidates_json TEXT NOT NULL DEFAULT '{}',
          last_error TEXT,
          retry_count INTEGER NOT NULL DEFAULT 0
        )
      `);

      // Migrations for items table
      try {
        await this.query('ALTER TABLE items ADD COLUMN triage_tags_json TEXT NOT NULL DEFAULT "{}"');
      } catch (e) {}
      try {
        await this.query('ALTER TABLE items ADD COLUMN all_candidates_json TEXT NOT NULL DEFAULT "{}"');
      } catch (e) {}

      await this.query(`
        CREATE TABLE IF NOT EXISTS meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
      `);

      await this.query(`
        CREATE TABLE IF NOT EXISTS profile_items (
          item_key TEXT PRIMARY KEY,
          item_version INTEGER NOT NULL,
          vector_json TEXT NOT NULL,
          tags_json TEXT NOT NULL
        )
      `);

      // Tier 1 Preference Memory Exemplar Storage
      await this.query(`
        CREATE TABLE IF NOT EXISTS exemplars (
          item_key TEXT NOT NULL,
          tag TEXT NOT NULL,
          label TEXT NOT NULL,
          vector_json TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          PRIMARY KEY (item_key, tag, label)
        )
      `);

      try {
        await this.query('CREATE INDEX IF NOT EXISTS idx_exemplars_tag ON exemplars(tag)');
        await this.query('CREATE INDEX IF NOT EXISTS idx_exemplars_item ON exemplars(item_key)');
      } catch (e) {}

      // Canonical candidate-level append-only event log
      await this.query(`
        CREATE TABLE IF NOT EXISTS interaction_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          item_key TEXT NOT NULL,
          input_hash TEXT,
          tag TEXT NOT NULL,
          action TEXT NOT NULL,
          score REAL,
          candidate_rank INTEGER,
          displayed_candidates_json TEXT,
          dense_score REAL,
          lexical_score REAL,
          nli_score REAL,
          classifier_version TEXT,
          taxonomy_version TEXT,
          timestamp TEXT NOT NULL
        )
      `);

      try {
        await this.query('CREATE INDEX IF NOT EXISTS idx_interaction_item_tag ON interaction_events(item_key, tag)');
        await this.query('CREATE INDEX IF NOT EXISTS idx_interaction_tag_action ON interaction_events(tag, action)');
      } catch (e) {}
    } catch (e) {
      if (typeof Zotero.log === 'function') {
        Zotero.log(`[zotero-organiser] StateStore table creation note: ${e}`);
      }
    }
  }

  private async query(sql: string, params: any[] = []): Promise<any[]> {
    if (!this.db) return [];
    if (typeof this.db.execute === 'function') {
      return await this.db.execute(sql, params);
    }
    if (typeof this.db.queryAsync === 'function') {
      return await this.db.queryAsync(sql, params);
    }
    return [];
  }

  async close(): Promise<void> {
    if (this.db) {
      const conn = this.db;
      this.db = null;
      try {
        await conn.close();
      } catch (e) {
        // Ignore close errors
      }
    }
  }

  async saveExemplar(
    itemKey: string,
    tag: string,
    label: 'positive' | 'negative',
    vector: number[],
    timestamp?: string
  ): Promise<void> {
    const ts = timestamp || new Date().toISOString();
    const oppLabel = label === 'positive' ? 'negative' : 'positive';

    if (this.db) {
      try {
        await this.query('DELETE FROM exemplars WHERE item_key = ? AND tag = ? AND label = ?', [
          itemKey,
          tag,
          oppLabel,
        ]);
        await this.query(
          `
          INSERT INTO exemplars (item_key, tag, label, vector_json, timestamp)
          VALUES (?, ?, ?, ?, ?)
          ON CONFLICT(item_key, tag, label) DO UPDATE SET
            vector_json = excluded.vector_json,
            timestamp = excluded.timestamp
          `,
          [itemKey, tag, label, JSON.stringify(vector), ts]
        );
      } catch (e) {
        if (typeof Zotero !== 'undefined' && Zotero.log) {
          Zotero.log(`[zotero-organiser] saveExemplar error: ${e}`);
        }
      }
    } else {
      // In-memory fallback
      this.memoryExemplars = this.memoryExemplars.filter(
        (e) => !(e.itemKey === itemKey && e.tag === tag)
      );
      this.memoryExemplars.push({
        itemKey,
        tag,
        label,
        vector,
        timestamp: ts,
      });
    }
  }

  async removeExemplar(itemKey: string, tag: string, label?: 'positive' | 'negative'): Promise<void> {
    if (this.db) {
      try {
        if (label) {
          await this.query('DELETE FROM exemplars WHERE item_key = ? AND tag = ? AND label = ?', [
            itemKey,
            tag,
            label,
          ]);
        } else {
          await this.query('DELETE FROM exemplars WHERE item_key = ? AND tag = ?', [itemKey, tag]);
        }
      } catch (e) {
        if (typeof Zotero !== 'undefined' && Zotero.log) {
          Zotero.log(`[zotero-organiser] removeExemplar error: ${e}`);
        }
      }
    } else {
      // In-memory fallback
      this.memoryExemplars = this.memoryExemplars.filter((e) => {
        if (e.itemKey !== itemKey || e.tag !== tag) return true;
        if (label && e.label !== label) return true;
        return false;
      });
    }
  }

  async loadAllExemplars(): Promise<Exemplar[]> {
    if (!this.db) {
      return [...this.memoryExemplars];
    }
    try {
      const rows = await this.query('SELECT item_key, tag, label, vector_json, timestamp FROM exemplars');
      if (!rows || rows.length === 0) return [];

      const getVal = (row: any, col: string) => {
        if (typeof row.getResultByName === 'function') {
          return row.getResultByName(col);
        }
        return row[col];
      };

      return rows.map((row: any) => {
        let vector: number[] = [];
        try {
          vector = JSON.parse(getVal(row, 'vector_json') || '[]');
        } catch (e) {
          vector = [];
        }
        return {
          itemKey: getVal(row, 'item_key'),
          tag: getVal(row, 'tag'),
          label: getVal(row, 'label') as 'positive' | 'negative',
          vector,
          timestamp: getVal(row, 'timestamp'),
        };
      });
    } catch (e) {
      return [];
    }
  }

  async getItem(itemKey: string): Promise<ItemRecord | null> {
    if (!this.db) {
      const mem = this.memoryItems.get(itemKey);
      if (!mem) return null;
      return {
        ...mem,
        autoTags: new Set(mem.autoTags),
        suppressedTags: new Set(mem.suppressedTags),
        triageTags: { ...mem.triageTags },
        candidateTags: { ...mem.candidateTags },
      };
    }
    try {
      const rows = await this.query('SELECT * FROM items WHERE item_key = ?', [itemKey]);
      if (!rows || rows.length === 0) return null;
      const row = rows[0];

      const getVal = (col: string) => {
        if (typeof row.getResultByName === 'function') {
          return row.getResultByName(col);
        }
        return row[col];
      };

      let triage: Record<string, number> = {};
      try {
        triage = JSON.parse(getVal('triage_tags_json') || '{}');
      } catch (e) {
        triage = {};
      }

      let candidates: Record<string, number> = {};
      try {
        candidates = JSON.parse(getVal('all_candidates_json') || '{}');
      } catch (e) {
        candidates = {};
      }

      return {
        itemKey: getVal('item_key'),
        zoteroVersion: getVal('zotero_version'),
        state: getVal('state'),
        discoveredAt: getVal('discovered_at'),
        readyAt: getVal('ready_at'),
        classifiedAt: getVal('classified_at'),
        taxonomyVersion: getVal('taxonomy_version'),
        classifierVersion: getVal('classifier_version'),
        inputHash: getVal('input_hash'),
        autoTags: new Set<string>(JSON.parse(getVal('auto_tags_json') || '[]')),
        suppressedTags: new Set<string>(JSON.parse(getVal('suppressed_tags_json') || '[]')),
        triageTags: triage,
        candidateTags: candidates,
        lastError: getVal('last_error'),
        retryCount: getVal('retry_count') || 0,
      };
    } catch (e) {
      return null;
    }
  }

  async saveItem(item: ItemRecord): Promise<void> {
    if (!this.db) {
      this.memoryItems.set(item.itemKey, {
        ...item,
        autoTags: new Set(item.autoTags),
        suppressedTags: new Set(item.suppressedTags),
        triageTags: { ...item.triageTags },
        candidateTags: { ...item.candidateTags },
      });
      return;
    }
    try {
      await this.query(
        `
        INSERT INTO items (
          item_key, zotero_version, state, discovered_at, ready_at, classified_at,
          taxonomy_version, classifier_version, input_hash, auto_tags_json,
          suppressed_tags_json, triage_tags_json, all_candidates_json, last_error, retry_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(item_key) DO UPDATE SET
          zotero_version = excluded.zotero_version,
          state = excluded.state,
          discovered_at = coalesce(excluded.discovered_at, items.discovered_at),
          ready_at = excluded.ready_at,
          classified_at = excluded.classified_at,
          taxonomy_version = excluded.taxonomy_version,
          classifier_version = excluded.classifier_version,
          input_hash = excluded.input_hash,
          auto_tags_json = excluded.auto_tags_json,
          suppressed_tags_json = excluded.suppressed_tags_json,
          triage_tags_json = excluded.triage_tags_json,
          all_candidates_json = excluded.all_candidates_json,
          last_error = excluded.last_error,
          retry_count = excluded.retry_count
        `,
        [
          item.itemKey,
          item.zoteroVersion,
          item.state,
          item.discoveredAt || new Date().toISOString(),
          item.readyAt || null,
          item.classifiedAt || null,
          item.taxonomyVersion || null,
          item.classifierVersion || null,
          item.inputHash || null,
          JSON.stringify([...item.autoTags]),
          JSON.stringify([...item.suppressedTags]),
          JSON.stringify(item.triageTags || {}),
          JSON.stringify(item.candidateTags || {}),
          item.lastError || null,
          item.retryCount,
        ]
      );
    } catch (e) {
      if (typeof Zotero !== 'undefined' && Zotero.log) {
        Zotero.log(`[zotero-organiser] saveItem error: ${e}`);
      }
    }
  }

  /**
   * Records a canonical interaction event into the append-only log.
   */
  async recordInteractionEvent(event: InteractionEvent): Promise<void> {
    if (!this.db) {
      this.memoryEvents.push({ ...event });
      return;
    }
    try {
      await this.query(
        `
        INSERT INTO interaction_events (
          item_key, input_hash, tag, action, score, candidate_rank,
          displayed_candidates_json, dense_score, lexical_score, nli_score,
          classifier_version, taxonomy_version, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `,
        [
          event.itemKey,
          event.inputHash || null,
          event.tag,
          event.action,
          event.score ?? null,
          event.candidateRank ?? null,
          event.displayedCandidates ? JSON.stringify(event.displayedCandidates) : null,
          event.denseScore ?? null,
          event.lexicalScore ?? null,
          event.nliScore ?? null,
          event.classifierVersion || null,
          event.taxonomyVersion || null,
          event.timestamp || new Date().toISOString(),
        ]
      );
    } catch (e) {
      // Non-blocking logging
    }
  }

  async acceptTriageTag(
    item: Zotero.Item | { key: string; [key: string]: any },
    tag: string,
    context: {
      rank?: number;
      displayed?: string[];
      score?: number;
      vector?: number[];
      classifierVersion?: string;
      taxonomyVersion?: string;
    } = {}
  ): Promise<ItemRecord | null> {
    const itemKey = item.key;
    const record = await this.getItem(itemKey);
    if (!record) return null;

    const conf = context.score ?? (record.triageTags[tag] || record.candidateTags[tag]);

    // Apply tag to Zotero
    if (typeof (item as any).getTags === 'function' && typeof (item as any).addTag === 'function') {
      const existing = (item as Zotero.Item).getTags().map((t: any) => t.tag);
      if (!existing.includes(tag)) {
        (item as Zotero.Item).addTag(tag, 1);
        if (typeof (item as Zotero.Item).saveTx === 'function') {
          await (item as Zotero.Item).saveTx();
        }
      }
    }

    record.autoTags.add(tag);
    record.suppressedTags.delete(tag);
    delete record.triageTags[tag];
    delete record.candidateTags[tag];

    const remainingTriage = Object.keys(record.triageTags).length;
    record.state = remainingTriage > 0 ? 'needs_triage' : 'organised';

    await this.saveItem(record);

    const vector = context.vector || extractDocumentVector(item);
    const timestamp = new Date().toISOString();

    if (vector && vector.length > 0) {
      await this.saveExemplar(itemKey, tag, 'positive', vector, timestamp);
      if (this.preferenceMemory) {
        this.preferenceMemory.addExemplar({
          itemKey,
          tag,
          label: 'positive',
          vector,
          timestamp,
        });
        this.preferenceMemory.removeExemplar(itemKey, tag, 'negative');
      }
    }

    await this.recordInteractionEvent({
      itemKey,
      inputHash: record.inputHash,
      tag,
      action: 'accepted',
      score: conf,
      candidateRank: context.rank,
      displayedCandidates: context.displayed,
      classifierVersion: context.classifierVersion || record.classifierVersion,
      taxonomyVersion: context.taxonomyVersion || record.taxonomyVersion,
      timestamp,
    });

    return record;
  }

  async rejectTriageTag(
    itemOrKey: Zotero.Item | { key: string; [key: string]: any } | string,
    tag: string,
    context: {
      rank?: number;
      displayed?: string[];
      score?: number;
      vector?: number[];
      classifierVersion?: string;
      taxonomyVersion?: string;
    } = {}
  ): Promise<ItemRecord | null> {
    const itemKey = typeof itemOrKey === 'string' ? itemOrKey : itemOrKey.key;
    const record = await this.getItem(itemKey);
    if (!record) return null;

    const conf = context.score ?? (record.triageTags[tag] || record.candidateTags[tag]);

    delete record.triageTags[tag];
    delete record.candidateTags[tag];
    record.suppressedTags.add(tag);
    record.autoTags.delete(tag);

    const remainingTriage = Object.keys(record.triageTags).length;
    record.state = remainingTriage > 0 ? 'needs_triage' : record.autoTags.size > 0 ? 'organised' : 'no_matches';

    await this.saveItem(record);

    let vector = context.vector;
    if (!vector && typeof itemOrKey !== 'string') {
      vector = extractDocumentVector(itemOrKey);
    } else if (!vector && typeof Zotero !== 'undefined' && Zotero.Items) {
      const zItem = Zotero.Items.get(itemKey as any);
      if (zItem) vector = extractDocumentVector(zItem);
    }

    const timestamp = new Date().toISOString();

    if (vector && vector.length > 0) {
      await this.saveExemplar(itemKey, tag, 'negative', vector, timestamp);
      if (this.preferenceMemory) {
        this.preferenceMemory.addExemplar({
          itemKey,
          tag,
          label: 'negative',
          vector,
          timestamp,
        });
        this.preferenceMemory.removeExemplar(itemKey, tag, 'positive');
      }
    }

    await this.recordInteractionEvent({
      itemKey,
      inputHash: record.inputHash,
      tag,
      action: 'rejected',
      score: conf,
      candidateRank: context.rank,
      displayedCandidates: context.displayed,
      classifierVersion: context.classifierVersion || record.classifierVersion,
      taxonomyVersion: context.taxonomyVersion || record.taxonomyVersion,
      timestamp,
    });

    return record;
  }

  async addCustomTaxonomyTag(
    item: Zotero.Item | { key: string; [key: string]: any },
    tag: string,
    taxonomyVersion?: string,
    vector?: number[]
  ): Promise<ItemRecord | null> {
    const itemKey = item.key;
    const record = await this.getItem(itemKey);
    if (!record) return null;

    if (typeof (item as any).getTags === 'function' && typeof (item as any).addTag === 'function') {
      const existing = (item as Zotero.Item).getTags().map((t: any) => t.tag);
      if (!existing.includes(tag)) {
        (item as Zotero.Item).addTag(tag, 1);
        if (typeof (item as Zotero.Item).saveTx === 'function') {
          await (item as Zotero.Item).saveTx();
        }
      }
    }

    record.autoTags.add(tag);
    record.suppressedTags.delete(tag);
    delete record.triageTags[tag];
    delete record.candidateTags[tag];

    record.state = Object.keys(record.triageTags).length > 0 ? 'needs_triage' : 'organised';

    await this.saveItem(record);

    const docVector = vector || extractDocumentVector(item);
    const timestamp = new Date().toISOString();

    if (docVector && docVector.length > 0) {
      await this.saveExemplar(itemKey, tag, 'positive', docVector, timestamp);
      if (this.preferenceMemory) {
        this.preferenceMemory.addExemplar({
          itemKey,
          tag,
          label: 'positive',
          vector: docVector,
          timestamp,
        });
        this.preferenceMemory.removeExemplar(itemKey, tag, 'negative');
      }
    }

    await this.recordInteractionEvent({
      itemKey,
      inputHash: record.inputHash,
      tag,
      action: 'manual_added',
      classifierVersion: record.classifierVersion,
      taxonomyVersion: taxonomyVersion || record.taxonomyVersion,
      timestamp,
    });

    return record;
  }

  async removeAutoTag(
    item: Zotero.Item | { key: string; [key: string]: any },
    tag: string,
    vector?: number[]
  ): Promise<ItemRecord | null> {
    const itemKey = item.key;
    const record = await this.getItem(itemKey);
    if (!record) return null;

    if (typeof (item as any).removeTag === 'function') {
      (item as Zotero.Item).removeTag(tag);
      if (typeof (item as Zotero.Item).saveTx === 'function') {
        await (item as Zotero.Item).saveTx();
      }
    }

    record.autoTags.delete(tag);
    record.suppressedTags.add(tag);
    const remainingTriage = Object.keys(record.triageTags).length;
    record.state = remainingTriage > 0 ? 'needs_triage' : record.autoTags.size > 0 ? 'organised' : 'no_matches';

    await this.saveItem(record);

    const docVector = vector || extractDocumentVector(item);
    const timestamp = new Date().toISOString();

    if (docVector && docVector.length > 0) {
      await this.saveExemplar(itemKey, tag, 'negative', docVector, timestamp);
      if (this.preferenceMemory) {
        this.preferenceMemory.addExemplar({
          itemKey,
          tag,
          label: 'negative',
          vector: docVector,
          timestamp,
        });
        this.preferenceMemory.removeExemplar(itemKey, tag, 'positive');
      }
    }

    await this.recordInteractionEvent({
      itemKey,
      inputHash: record.inputHash,
      tag,
      action: 'removed',
      classifierVersion: record.classifierVersion,
      taxonomyVersion: record.taxonomyVersion,
      timestamp,
    });

    return record;
  }

  async unsuppressTag(itemKey: string, tag: string): Promise<ItemRecord | null> {
    const record = await this.getItem(itemKey);
    if (record) {
      record.suppressedTags.delete(tag);
      await this.saveItem(record);
    }

    await this.removeExemplar(itemKey, tag, 'negative');
    if (this.preferenceMemory) {
      this.preferenceMemory.removeExemplar(itemKey, tag, 'negative');
    }

    await this.recordInteractionEvent({
      itemKey,
      inputHash: record ? record.inputHash : undefined,
      tag,
      action: 'unsuppressed',
      classifierVersion: record ? record.classifierVersion : undefined,
      taxonomyVersion: record ? record.taxonomyVersion : undefined,
      timestamp: new Date().toISOString(),
    });

    return record;
  }

  async recordError(itemKey: string, error: string): Promise<void> {
    if (!this.db) {
      const item = this.memoryItems.get(itemKey);
      if (item) {
        item.state = 'error';
        item.lastError = error;
        item.retryCount += 1;
      }
      return;
    }
    try {
      await this.query(
        `
        UPDATE items
        SET state = 'error', last_error = ?, retry_count = retry_count + 1
        WHERE item_key = ?
        `,
        [error, itemKey]
      );
    } catch (e) {
      // Ignore
    }
  }

  async getMeta(key: string): Promise<string | null> {
    if (!this.db) {
      return this.memoryMeta.get(key) || null;
    }
    try {
      const rows = await this.query('SELECT value FROM meta WHERE key = ?', [key]);
      if (!rows || rows.length === 0) return null;
      const row = rows[0];
      return typeof row.getResultByName === 'function' ? row.getResultByName('value') : row.value;
    } catch (e) {
      return null;
    }
  }

  async setMeta(key: string, value: string): Promise<void> {
    if (!this.db) {
      this.memoryMeta.set(key, value);
      return;
    }
    try {
      await this.query(
        `
        INSERT INTO meta (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        `,
        [key, value]
      );
    } catch (e) {
      // Ignore
    }
  }

  async getActiveTaxonomyYaml(): Promise<string | null> {
    return await this.getMeta('active_taxonomy_yaml');
  }

  async setActiveTaxonomyYaml(yaml: string): Promise<void> {
    await this.setMeta('active_taxonomy_yaml', yaml);
  }

  async establishBaseline(libraryVersion: number): Promise<string> {
    const timestamp = new Date().toISOString();
    await this.setMeta('library_version', String(libraryVersion));
    await this.setMeta('baseline_at', timestamp);
    return timestamp;
  }

  async getBaseline(): Promise<{ libraryVersion: number | null; baselineAt: string | null }> {
    const ver = await this.getMeta('library_version');
    const at = await this.getMeta('baseline_at');
    return {
      libraryVersion: ver ? parseInt(ver, 10) : null,
      baselineAt: at,
    };
  }
}


