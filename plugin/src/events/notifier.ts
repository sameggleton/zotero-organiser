import { computeDocumentVector, computeInputHash, documentText, extractDocumentVector, extractItemData, ItemData } from '../core/document.js';
import { decide } from '../core/policy.js';
import { reconcile } from '../core/reconcile.js';
import { ItemRecord, StateStore } from '../core/state.js';
import { ClassifierEngine } from '../classifier/engine.js';
import { Taxonomy } from '../core/taxonomy.js';

export interface NotifierOptions {
  writeEnabled: boolean;
  onlyNewItems: boolean;
  allowTagRemoval: boolean;
  autoThreshold: number;
  triageThreshold: number;
  settleMs: number;
}

export class OrganiserNotifier {
  private observerID: string | null = null;
  private stateStore: StateStore;
  private classifier: ClassifierEngine;
  private taxonomy: Taxonomy;
  private options: NotifierOptions;
  private settleTimeouts = new Map<string, number>();

  constructor(
    stateStore: StateStore,
    classifier: ClassifierEngine,
    taxonomy: Taxonomy,
    options: NotifierOptions
  ) {
    this.stateStore = stateStore;
    this.classifier = classifier;
    this.taxonomy = taxonomy;
    this.options = options;
  }

  public getTaxonomy(): Taxonomy {
    return this.taxonomy;
  }

  public updateTaxonomy(taxonomy: Taxonomy): void {
    this.taxonomy = taxonomy;
  }

  public init(): void {
    if (typeof Zotero === 'undefined' || !Zotero.Notifier) {
      return;
    }

    this.observerID = Zotero.Notifier.registerObserver(
      {
        notify: (event, type, ids, extraData) => {
          this.handleNotification(event, type, ids, extraData).catch((err) => {
            if (typeof Zotero !== 'undefined' && Zotero.log) {
              Zotero.log(`[zotero-organiser] error in notifier: ${err}`);
            }
          });
        },
      },
      ['item', 'item-tag'],
      'zotero-organiser'
    );
  }

  public destroy(): void {
    if (this.observerID && typeof Zotero !== 'undefined' && Zotero.Notifier) {
      Zotero.Notifier.unregisterObserver(this.observerID);
      this.observerID = null;
    }
    for (const timeout of this.settleTimeouts.values()) {
      clearTimeout(timeout);
    }
    this.settleTimeouts.clear();
  }

  public updateOptions(options: Partial<NotifierOptions>): void {
    this.options = { ...this.options, ...options };
  }

  private async handleNotification(
    event: Zotero.Notifier.EventType,
    type: Zotero.Notifier.ItemType,
    ids: (string | number)[],
    extraData: Record<string, any>
  ): Promise<void> {
    if (type === 'item' && (event === 'add' || event === 'modify')) {
      for (const id of ids) {
        const item = Zotero.Items.get(Number(id));
        if (item && item.isRegularItem() && !item.isFeedItem) {
          this.scheduleProcess(item);
        }
      }
    } else if (type === 'item-tag' && event === 'delete') {
      await this.handleTagDeleted(ids, extraData);
    }
  }

  private scheduleProcess(item: Zotero.Item): void {
    const key = item.key;
    if (this.settleTimeouts.has(key)) {
      clearTimeout(this.settleTimeouts.get(key));
    }

    const timeout = window.setTimeout(async () => {
      this.settleTimeouts.delete(key);
      try {
        await this.processItem(item);
      } catch (err: any) {
        if (typeof Zotero !== 'undefined' && Zotero.log) {
          Zotero.log(`[zotero-organiser] failed to process item ${key}: ${err}`);
        }
      }
    }, this.options.settleMs);

    this.settleTimeouts.set(key, timeout);
  }

  public async processItem(
    item: Zotero.Item,
    force = false,
    dryRun = false
  ): Promise<{ status: string; appliedTags?: string[]; decision?: any }> {
    const itemData = extractItemData(item);
    let stored = await this.stateStore.getItem(itemData.key);

    if (!stored) {
      stored = {
        itemKey: itemData.key,
        zoteroVersion: itemData.version,
        state: 'discovered',
        autoTags: new Set<string>(),
        suppressedTags: new Set<string>(),
        triageTags: {},
        candidateTags: {},
        retryCount: 0,
      };
      await this.stateStore.saveItem(stored);
    }

    const currentTags = new Set(itemData.tags);
    const manualTags = new Set([...currentTags].filter((t) => !stored!.autoTags.has(t)));
    const inputHash = await computeInputHash(
      itemData,
      this.taxonomy.version,
      this.classifier.version,
      manualTags
    );

    if (!force && stored.inputHash === inputHash && (stored.state === 'organised' || stored.state === 'needs_triage')) {
      return { status: 'skipped_unchanged' };
    }

    const docText = documentText(itemData);
    const docVector = computeDocumentVector(docText);
    const allRanked = this.classifier.rankAllCandidates(docText, docVector);

    // Primary candidates for triage review
    const triageMap: Record<string, number> = {};
    const candidateMap: Record<string, number> = {};

    for (const cand of allRanked) {
      if (stored.suppressedTags.has(cand.tag) || stored.autoTags.has(cand.tag)) {
        continue;
      }
      if (cand.score >= this.options.triageThreshold) {
        triageMap[cand.tag] = cand.score;
      } else {
        candidateMap[cand.tag] = cand.score;
      }
    }

    // Always-Triage: do not auto-write tags directly to Zotero without user confirmation
    let nextState: ItemRecord['state'] = 'organised';
    if (Object.keys(triageMap).length > 0) {
      nextState = 'needs_triage';
    } else if (stored.autoTags.size > 0) {
      nextState = 'organised';
    } else {
      nextState = 'no_matches';
    }

    stored.state = nextState;
    stored.triageTags = triageMap;
    stored.candidateTags = candidateMap;
    stored.inputHash = inputHash;
    stored.taxonomyVersion = this.taxonomy.version;
    stored.classifierVersion = this.classifier.version;
    stored.classifiedAt = new Date().toISOString();

    await this.stateStore.saveItem(stored);

    if (typeof Zotero !== 'undefined' && Zotero.log) {
      Zotero.log(
        `[zotero-organiser] classified item ${item.key}: ${Object.keys(triageMap).length} triage candidates found, state=${stored.state}`
      );
    }

    return {
      status: 'success',
      appliedTags: Array.from(stored.autoTags),
      decision: { accepted: new Set(), held: new Set(Object.keys(triageMap)), ignored: new Set() },
    };
  }

  private async handleTagDeleted(
    ids: (string | number)[],
    extraData: Record<string, any>
  ): Promise<void> {
    for (const itemID of ids) {
      const item = Zotero.Items.get(Number(itemID));
      if (!item || !item.isRegularItem()) continue;

      const stored = await this.stateStore.getItem(item.key);
      if (!stored) continue;

      const currentTags = new Set(item.getTags().map((t: any) => t.tag));
      let stateChanged = false;

      for (const autoTag of stored.autoTags) {
        if (!currentTags.has(autoTag)) {
          stored.autoTags.delete(autoTag);
          stored.suppressedTags.add(autoTag);
          stateChanged = true;

          const docVector = extractDocumentVector(item);
          await this.stateStore.saveExemplar(item.key, autoTag, 'negative', docVector);
          const prefMem = this.stateStore.getPreferenceMemory();
          if (prefMem) {
            prefMem.addExemplar({
              itemKey: item.key,
              tag: autoTag,
              label: 'negative',
              vector: docVector,
              timestamp: new Date().toISOString(),
            });
            prefMem.removeExemplar(item.key, autoTag, 'positive');
          }
          await this.stateStore.removeExemplar(item.key, autoTag, 'positive');

          if (typeof Zotero !== 'undefined' && Zotero.log) {
            Zotero.log(
              `[zotero-organiser] user removed auto tag "${autoTag}" on ${item.key}; marking suppressed and recording negative exemplar`
            );
          }
        }
      }

      if (stateChanged) {
        await this.stateStore.saveItem(stored);
      }
    }
  }
}
