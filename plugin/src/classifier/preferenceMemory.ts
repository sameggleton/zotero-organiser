/**
 * Tier 1: Preference Memory
 * 
 * Maintains embedding-centroid prototypes and k-NN exemplars of user-confirmed positive
 * and explicitly rejected negative tags.
 * 
 * Computes a bounded personalization residual:
 *   personalized_score = base_score + alpha * sim(positive_exemplars) - beta * sim(negative_exemplars)
 * 
 * Operates strictly in bounded shadow/rerank mode to protect taxonomy integrity.
 */

export interface Exemplar {
  itemKey: string;
  vector: number[];
  tag: string;
  label: 'positive' | 'negative';
  timestamp: string;
}

export interface Prototype {
  tag: string;
  positiveCentroid: number[] | null;
  negativeCentroid: number[] | null;
  positiveCount: number;
  negativeCount: number;
}

export interface PreferenceMemoryConfig {
  alpha?: number; // positive boost weight (default: 0.12)
  beta?: number;  // negative suppression weight (default: 0.15)
  maxResidual?: number; // hard bound clamp on residual (default: 0.18)
  topK?: number; // k-NN neighbours to inspect (default: 5)
}

export class PreferenceMemory {
  private positiveExemplars = new Map<string, Exemplar[]>(); // tag -> positive exemplars
  private negativeExemplars = new Map<string, Exemplar[]>(); // tag -> negative exemplars
  private config: Required<PreferenceMemoryConfig>;

  constructor(config: PreferenceMemoryConfig = {}) {
    this.config = {
      alpha: config.alpha ?? 0.12,
      beta: config.beta ?? 0.15,
      maxResidual: config.maxResidual ?? 0.18,
      topK: config.topK ?? 5,
    };
  }

  /**
   * Adds an exemplar to memory.
   * Automatically clears any existing opposite-label exemplar for the same itemKey and tag.
   */
  public addExemplar(exemplar: Exemplar): void {
    const map = exemplar.label === 'positive' ? this.positiveExemplars : this.negativeExemplars;
    const oppMap = exemplar.label === 'positive' ? this.negativeExemplars : this.positiveExemplars;

    // Remove from opposite map if present
    const oppList = oppMap.get(exemplar.tag);
    if (oppList) {
      oppMap.set(exemplar.tag, oppList.filter((e) => e.itemKey !== exemplar.itemKey));
    }

    if (!map.has(exemplar.tag)) {
      map.set(exemplar.tag, []);
    }
    const list = map.get(exemplar.tag)!;
    // Prevent duplicate entries for the same itemKey and tag
    const idx = list.findIndex((e) => e.itemKey === exemplar.itemKey);
    if (idx >= 0) {
      list[idx] = exemplar;
    } else {
      list.push(exemplar);
    }
  }

  /**
   * Removes an exemplar if an interaction is undone or unsuppressed.
   */
  public removeExemplar(itemKey: string, tag: string, label?: 'positive' | 'negative'): void {
    if (!label || label === 'positive') {
      const pos = this.positiveExemplars.get(tag);
      if (pos) {
        this.positiveExemplars.set(tag, pos.filter((e) => e.itemKey !== itemKey));
      }
    }
    if (!label || label === 'negative') {
      const neg = this.negativeExemplars.get(tag);
      if (neg) {
        this.negativeExemplars.set(tag, neg.filter((e) => e.itemKey !== itemKey));
      }
    }
  }

  /**
   * Clears all exemplars from memory.
   */
  public clear(): void {
    this.positiveExemplars.clear();
    this.negativeExemplars.clear();
  }

  /**
   * Returns all stored exemplars.
   */
  public getAllExemplars(): Exemplar[] {
    const results: Exemplar[] = [];
    for (const list of this.positiveExemplars.values()) {
      results.push(...list);
    }
    for (const list of this.negativeExemplars.values()) {
      results.push(...list);
    }
    return results;
  }

  /**
   * Returns exemplars for a specific tag.
   */
  public getExemplars(tag: string, label?: 'positive' | 'negative'): Exemplar[] {
    if (label === 'positive') {
      return [...(this.positiveExemplars.get(tag) || [])];
    }
    if (label === 'negative') {
      return [...(this.negativeExemplars.get(tag) || [])];
    }
    return [
      ...(this.positiveExemplars.get(tag) || []),
      ...(this.negativeExemplars.get(tag) || []),
    ];
  }

  /**
   * Computes the bounded personalization residual for a given document vector and tag.
   * 
   * residual in [-maxResidual, +maxResidual]
   */
  public computeResidual(docVector: number[], tag: string): { residual: number; posSim: number; negSim: number } {
    if (!docVector || docVector.length === 0) {
      return { residual: 0, posSim: 0, negSim: 0 };
    }

    const posExemplars = this.positiveExemplars.get(tag) || [];
    const negExemplars = this.negativeExemplars.get(tag) || [];

    const posSim = this.computeTopKSimilarity(docVector, posExemplars, this.config.topK);
    const negSim = this.computeTopKSimilarity(docVector, negExemplars, this.config.topK);

    let rawResidual = this.config.alpha * posSim - this.config.beta * negSim;

    // Hard bound clamping to prevent overriding taxonomy invariants
    const clampedResidual = Math.max(-this.config.maxResidual, Math.min(this.config.maxResidual, rawResidual));

    return {
      residual: clampedResidual,
      posSim,
      negSim,
    };
  }

  /**
   * Reranks a candidate set by applying bounded personalization residuals.
   */
  public rerank(
    docVector: number[],
    candidates: Array<{ tag: string; baseScore: number; [key: string]: any }>
  ): Array<{ tag: string; baseScore: number; personalizedScore: number; residual: number; [key: string]: any }> {
    return candidates.map((c) => {
      const { residual, posSim, negSim } = this.computeResidual(docVector, c.tag);
      const personalizedScore = Math.max(0.0, Math.min(1.0, c.baseScore + residual));
      return {
        ...c,
        baseScore: c.baseScore,
        personalizedScore,
        residual,
        posSim,
        negSim,
      };
    }).sort((a, b) => b.personalizedScore - a.personalizedScore);
  }

  /**
   * Computes the mean cosine similarity of top-K closest exemplars.
   */
  private computeTopKSimilarity(docVector: number[], exemplars: Exemplar[], k: number): number {
    if (exemplars.length === 0) return 0;

    const sims = exemplars.map((e) => this.cosineSimilarity(docVector, e.vector));
    sims.sort((a, b) => b - a);

    const topKSims = sims.slice(0, Math.min(k, sims.length));
    const sum = topKSims.reduce((acc, v) => acc + Math.max(0, v), 0);
    return sum / topKSims.length;
  }

  /**
   * Fast vector cosine similarity.
   */
  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length || a.length === 0) return 0;

    let dot = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    if (normA === 0 || normB === 0) return 0;
    return dot / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  /**
   * Returns summary counts of stored memory.
   */
  public getStats(): { positiveCount: number; negativeCount: number; coveredTags: number } {
    let positiveCount = 0;
    let negativeCount = 0;
    const tags = new Set<string>();

    for (const [tag, list] of this.positiveExemplars.entries()) {
      positiveCount += list.length;
      if (list.length > 0) tags.add(tag);
    }
    for (const [tag, list] of this.negativeExemplars.entries()) {
      negativeCount += list.length;
      if (list.length > 0) tags.add(tag);
    }

    return {
      positiveCount,
      negativeCount,
      coveredTags: tags.size,
    };
  }
}
