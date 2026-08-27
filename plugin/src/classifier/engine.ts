import { computeDocumentVector } from '../core/document.js';
import { Taxonomy } from '../core/taxonomy.js';
import { HybridRanker } from './hybridRanker.js';
import { PreferenceMemory } from './preferenceMemory.js';
import { RemoteClassifier } from './remoteClassifier.js';
import { ClassificationResult, ClassifierEngineConfig, TagScore } from './types.js';

export class ClassifierEngine {
  public preferenceMemory: PreferenceMemory;
  private taxonomy: Taxonomy;
  private ranker: HybridRanker;
  private config: ClassifierEngineConfig;
  private remoteClassifier: RemoteClassifier | null = null;

  constructor(taxonomy: Taxonomy, config: ClassifierEngineConfig, preferenceMemory?: PreferenceMemory) {
    this.taxonomy = taxonomy;
    this.config = config;
    this.ranker = new HybridRanker(taxonomy);
    this.preferenceMemory = preferenceMemory || new PreferenceMemory();

    if (config.mode === 'remote' && config.remoteEndpoint && config.remoteApiKey) {
      this.remoteClassifier = new RemoteClassifier(taxonomy, {
        endpoint: config.remoteEndpoint,
        apiKey: config.remoteApiKey,
        model: config.remoteModel,
      });
    }
  }

  get version(): string {
    if (this.remoteClassifier) {
      return this.remoteClassifier.version;
    }
    return 'local-ranker:lexical';
  }

  public updateTaxonomy(taxonomy: Taxonomy): void {
    this.taxonomy = taxonomy;
    this.ranker = new HybridRanker(taxonomy);
    if (this.config.mode === 'remote' && this.config.remoteEndpoint && this.config.remoteApiKey) {
      this.remoteClassifier = new RemoteClassifier(taxonomy, {
        endpoint: this.config.remoteEndpoint,
        apiKey: this.config.remoteApiKey,
        model: this.config.remoteModel,
      });
    }
  }

  /**
   * Classifies document text, applying PreferenceMemory residuals and taxonomy constraints.
   */
  public async classify(document: string, docVector?: number[]): Promise<ClassificationResult> {
    const vec = docVector || computeDocumentVector(document);

    if (this.remoteClassifier) {
      const candidates = this.ranker.rank(document);
      const allowed = new Set(candidates.map((c) => c.tag));
      const rawTags = await this.remoteClassifier.classify(document, allowed);
      
      const personalizedTags: TagScore[] = rawTags.map((t) => {
        const { residual } = this.preferenceMemory.computeResidual(vec, t.tag);
        const confidence = Math.max(0.0, Math.min(1.0, t.confidence + residual));
        return {
          tag: t.tag,
          confidence,
          baseScore: t.confidence,
          residual,
        };
      }).sort((a, b) => b.confidence - a.confidence);

      return {
        tags: this.enforceTaxonomyConstraints(personalizedTags),
        version: this.version,
      };
    }

    // Default local lexical scoring calibrated to decision thresholds
    const candidates = this.ranker.rank(document);
    const tags: TagScore[] = candidates
      .filter((c) => c.lexicalScore > 0)
      .map((c) => {
        // High confidence (>= 0.85) for strong lexical overlap, moderate (0.70 - 0.84) for single matches
        const baseScore = Math.min(0.96, 0.70 + Math.min(0.26, c.lexicalScore * 0.18));
        const { residual } = this.preferenceMemory.computeResidual(vec, c.tag);
        const confidence = Math.max(0.0, Math.min(1.0, baseScore + residual));
        return {
          tag: c.tag,
          confidence,
          baseScore,
          residual,
        };
      })
      .sort((a, b) => b.confidence - a.confidence);

    return {
      tags: this.enforceTaxonomyConstraints(tags),
      version: this.version,
    };
  }

  /**
   * Ranks all eligible taxonomy tags for a document, incorporating PreferenceMemory residuals.
   */
  public rankAllCandidates(
    document: string,
    docVector?: number[]
  ): Array<{ tag: string; score: number; baseScore: number; residual: number }> {
    const candidates = this.ranker.rank(document, {}, 30, 20, 5);
    const allTaxonomyTags = Array.from(this.taxonomy.classifierTags());
    const seen = new Set(candidates.map((c) => c.tag));
    const vec = docVector || computeDocumentVector(document);

    const results: Array<{ tag: string; score: number; baseScore: number; residual: number }> = candidates.map((c) => {
      const baseScore = c.lexicalScore > 0 ? Math.min(0.96, 0.70 + Math.min(0.26, c.lexicalScore * 0.18)) : 0.45;
      const { residual } = this.preferenceMemory.computeResidual(vec, c.tag);
      const score = Math.max(0.0, Math.min(1.0, baseScore + residual));
      return { tag: c.tag, score, baseScore, residual };
    });

    for (const tag of allTaxonomyTags) {
      if (!seen.has(tag)) {
        const baseScore = 0.35;
        const { residual } = this.preferenceMemory.computeResidual(vec, tag);
        const score = Math.max(0.0, Math.min(1.0, baseScore + residual));
        results.push({ tag, score, baseScore, residual });
      }
    }

    return results.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.tag.localeCompare(b.tag);
    });
  }

  /**
   * Enforces taxonomy constraints:
   * 1. Only eligible classifier tags are permitted.
   * 2. Namespace max_tags quota is strictly capped.
   * 3. Namespace mutual exclusivity is strictly enforced (at most 1 tag).
   */
  public enforceTaxonomyConstraints(tags: TagScore[]): TagScore[] {
    const eligible = this.taxonomy.classifierTags();
    const namespaceCounts = new Map<string, number>();
    const filtered: TagScore[] = [];

    for (const item of tags) {
      if (!eligible.has(item.tag)) continue;

      const slashIdx = item.tag.indexOf('/');
      if (slashIdx === -1) continue;
      const ns = item.tag.substring(0, slashIdx);
      const nsDef = this.taxonomy.namespaces[ns];

      const maxTags = nsDef ? (nsDef.mutually_exclusive ? 1 : nsDef.max_tags) : 1;
      const currentCount = namespaceCounts.get(ns) || 0;

      if (currentCount < maxTags) {
        filtered.push(item);
        namespaceCounts.set(ns, currentCount + 1);
      }
    }

    return filtered;
  }
}

