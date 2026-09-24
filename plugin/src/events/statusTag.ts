import { ItemRecord, StateStore } from '../core/state.js';
import { Taxonomy } from '../core/taxonomy.js';

export const STATUS_NAMESPACE = 'status';
export const DEFAULT_STATUS_TAG = 'status/to-read';

export interface StatusTagOptions {
  statusTagEnabled: boolean;
  statusTagName: string;
  writeEnabled: boolean;
}

export type StatusTagResult =
  | 'applied'
  | 'skipped_disabled'
  | 'skipped_writes_disabled'
  | 'skipped_invalid_tag'
  | 'skipped_invalid_item'
  | 'skipped_existing_status'
  | 'skipped_already_tracked'
  | 'skipped_suppressed'
  | 'skipped_write_failed';

export function statusTagsFromTaxonomy(taxonomy: Taxonomy): string[] {
  const namespace = taxonomy.namespaces[STATUS_NAMESPACE];
  if (!namespace) return [];
  return Object.keys(namespace.values).map((label) => `${STATUS_NAMESPACE}/${label}`);
}

/**
 * Keep a requested tag only when it is one of the taxonomy's status values.
 * Otherwise fall back to the default, then to the first defined status tag.
 */
export function resolveStatusTag(requested: string, allowed: readonly string[]): string | null {
  const trimmed = (requested || '').trim();
  if (allowed.includes(trimmed)) return trimmed;
  if (allowed.includes(DEFAULT_STATUS_TAG)) return DEFAULT_STATUS_TAG;
  return allowed[0] ?? null;
}

export class StatusTagService {
  private stateStore: StateStore;
  private options: StatusTagOptions;
  private allowedTags: Set<string>;

  constructor(stateStore: StateStore, options: StatusTagOptions, taxonomy: Taxonomy) {
    this.stateStore = stateStore;
    this.options = options;
    this.allowedTags = new Set(statusTagsFromTaxonomy(taxonomy));
  }

  public updateOptions(options: Partial<StatusTagOptions>): void {
    this.options = { ...this.options, ...options };
  }

  public updateTaxonomy(taxonomy: Taxonomy): void {
    this.allowedTags = new Set(statusTagsFromTaxonomy(taxonomy));
  }

  public getStatusTagName(): string {
    return this.options.statusTagName;
  }

  public getAllowedTags(): string[] {
    return [...this.allowedTags];
  }

  public async applyToItem(item: Zotero.Item): Promise<StatusTagResult> {
    if (!item || typeof item.isRegularItem !== 'function' || !item.isRegularItem() || item.isFeedItem) {
      return 'skipped_invalid_item';
    }

    if (!this.options.statusTagEnabled) {
      return 'skipped_disabled';
    }

    let stored = await this.stateStore.getItem(item.key);
    if (stored?.statusTag) {
      const currentTags = new Set(this.tagNames(item));
      if (currentTags.has(stored.statusTag)) {
        return 'skipped_already_tracked';
      }
      await this.suppressStatusTag(stored, stored.statusTag);
      return 'skipped_suppressed';
    }

    if (!this.options.writeEnabled) {
      return 'skipped_writes_disabled';
    }

    const tagName = (this.options.statusTagName || '').trim();
    if (!tagName) {
      return 'skipped_disabled';
    }
    if (!this.allowedTags.has(tagName)) {
      return 'skipped_invalid_tag';
    }
    if (stored?.suppressedTags.has(tagName)) {
      return 'skipped_suppressed';
    }

    const existingTags = this.tagNames(item);
    if (existingTags.some((tag) => tag === tagName || tag.startsWith(`${STATUS_NAMESPACE}/`))) {
      return 'skipped_existing_status';
    }

    if (typeof item.addTag !== 'function' || typeof item.saveTx !== 'function') {
      return 'skipped_write_failed';
    }

    if (!stored) {
      stored = this.createRecord(item);
    }

    // Type 0 keeps the reading tag visible. Type 1 is an automatic tag, which Zotero hides
    // when "Show automatic tags" is off.
    item.addTag(tagName, 0);
    const saved = await item.saveTx();
    if (saved === false) {
      return 'skipped_write_failed';
    }

    stored.statusTag = tagName;
    await this.stateStore.saveItem(stored);

    if (typeof Zotero !== 'undefined' && Zotero.log) {
      Zotero.log(`[zotero-organiser] applied status tag "${tagName}" to item ${item.key}`);
    }

    return 'applied';
  }

  /**
   * Called when a tag is removed from an item. If the removed tag was the
   * status tag, clears tracking and suppresses it so it is never re-added.
   * Returns true if the removed tag was the status tag.
   */
  public async handleStatusTagRemoved(item: Zotero.Item, stored: ItemRecord): Promise<boolean> {
    const tagName = stored.statusTag;
    if (!tagName) {
      return false;
    }

    const currentTags = new Set(this.tagNames(item));
    if (currentTags.has(tagName)) {
      return false;
    }

    await this.suppressStatusTag(stored, tagName);
    return true;
  }

  private async suppressStatusTag(stored: ItemRecord, tagName: string): Promise<void> {
    stored.statusTag = null;
    stored.suppressedTags.add(tagName);
    await this.stateStore.saveItem(stored);

    if (typeof Zotero !== 'undefined' && Zotero.log) {
      Zotero.log(
        `[zotero-organiser] user removed status tag "${tagName}" on ${stored.itemKey}; marking suppressed`
      );
    }
  }

  private tagNames(item: Zotero.Item): string[] {
    if (typeof item.getTags !== 'function') return [];
    return item.getTags().map((entry: { tag: string }) => entry.tag);
  }

  private createRecord(item: Zotero.Item): ItemRecord {
    return {
      itemKey: item.key,
      zoteroVersion: item.version || 0,
      state: 'discovered',
      autoTags: new Set<string>(),
      suppressedTags: new Set<string>(),
      triageTags: {},
      candidateTags: {},
      statusTag: null,
      retryCount: 0,
    };
  }
}
