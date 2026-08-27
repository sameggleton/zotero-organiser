export interface ItemData {
  key: string;
  version: number;
  itemType: string;
  title: string;
  abstractNote?: string;
  publicationTitle?: string;
  tags: string[];
}

export function extractItemData(item: Zotero.Item | Record<string, any>): ItemData {
  if (typeof (item as any).getField === 'function') {
    const zItem = item as Zotero.Item;
    return {
      key: zItem.key,
      version: zItem.version,
      itemType: zItem.itemType,
      title: zItem.getField('title') || '',
      abstractNote: zItem.getField('abstractNote') || '',
      publicationTitle: zItem.getField('publicationTitle') || '',
      tags: (zItem.getTags() || []).map((t) => t.tag),
    };
  }

  // Fallback if plain JSON passed
  const data = (item as any).data || item;
  return {
    key: data.key || (item as any).key || '',
    version: data.version || (item as any).version || 0,
    itemType: data.itemType || '',
    title: data.title || '',
    abstractNote: data.abstractNote || '',
    publicationTitle: data.publicationTitle || '',
    tags: Array.isArray(data.tags)
      ? data.tags.map((t: any) => (typeof t === 'string' ? t : t.tag))
      : [],
  };
}

/**
 * Produces structured textual document representation for embeddings / classification.
 */
export function documentText(itemData: ItemData): string {
  const parts: string[] = [];

  if (itemData.title) {
    parts.push(`Title: ${itemData.title.trim()}`);
  }
  if (itemData.abstractNote) {
    parts.push(`Abstract: ${itemData.abstractNote.trim()}`);
  }
  if (itemData.publicationTitle) {
    parts.push(`Publication: ${itemData.publicationTitle.trim()}`);
  }
  if (itemData.itemType) {
    parts.push(`Type: ${itemData.itemType}`);
  }
  if (itemData.tags && itemData.tags.length > 0) {
    parts.push(`Tags: ${[...itemData.tags].sort().join(', ')}`);
  }

  return parts.join('\n\n');
}

/**
 * Computes deterministic SHA-256 hash of item metadata and taxonomy version to detect changes.
 */
export async function computeInputHash(
  itemData: ItemData,
  taxonomyVersion: string,
  classifierVersion: string,
  manualTags: Set<string>
): Promise<string> {
  const payload = {
    title: itemData.title,
    abstractNote: itemData.abstractNote || '',
    publicationTitle: itemData.publicationTitle || '',
    itemType: itemData.itemType,
    manualTags: [...manualTags].sort(),
    taxonomyVersion,
    classifierVersion,
  };

  const jsonStr = JSON.stringify(payload);
  const msgUint8 = new TextEncoder().encode(jsonStr);

  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  }

  // Fallback simple hash if running in environments without crypto.subtle
  let hash = 0;
  for (let i = 0; i < jsonStr.length; i++) {
    const char = jsonStr.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return `hash-${Math.abs(hash).toString(16)}`;
}

/**
 * Simple deterministic string hash (FNV-1a 32-bit).
 */
function hashString(str: string): number {
  let hash = 2166136261;
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

/**
 * Computes an L2-normalized fixed-dimension term frequency vector using feature hashing.
 *
 * @param text Document string
 * @param dimensions Vector dimensionality (default: 64)
 * @returns Normalized vector with unit L2 length (or zero vector if empty)
 */
export function computeDocumentVector(text: string, dimensions = 64): number[] {
  if (!text || text.trim().length === 0) {
    return new Array(dimensions).fill(0);
  }

  const stopwords = new Set([
    'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'this', 'that', 'these', 'those', 'it', 'its', 'as', 'from', 'into', 'which'
  ]);

  const tokens = text
    .toLowerCase()
    .match(/\b[a-zA-Z0-9_\-]+\b/g)
    ?.filter((t) => t.length > 2 && !stopwords.has(t)) || [];

  if (tokens.length === 0) {
    return new Array(dimensions).fill(0);
  }

  const vec = new Array(dimensions).fill(0);

  for (const token of tokens) {
    const h = hashString(token);
    const index = h % dimensions;
    vec[index] += 1;
  }

  // L2 normalize
  let sumSq = 0;
  for (let i = 0; i < dimensions; i++) {
    sumSq += vec[i] * vec[i];
  }

  if (sumSq > 0) {
    const norm = Math.sqrt(sumSq);
    for (let i = 0; i < dimensions; i++) {
      vec[i] /= norm;
    }
  }

  return vec;
}

/**
 * Extracts or computes a document vector from various inputs (Item, ItemData, string, or existing vector).
 */
export function extractDocumentVector(
  item: Zotero.Item | ItemData | Record<string, any> | string | number[],
  dimensions = 64
): number[] {
  if (!item) {
    return new Array(dimensions).fill(0);
  }

  if (Array.isArray(item)) {
    return item;
  }

  if (typeof item === 'string') {
    return computeDocumentVector(item, dimensions);
  }

  // If object already contains vector or vector_json
  if ((item as any).vector && Array.isArray((item as any).vector)) {
    return (item as any).vector;
  }

  const itemData = extractItemData(item);
  const text = documentText(itemData);
  return computeDocumentVector(text, dimensions);
}

