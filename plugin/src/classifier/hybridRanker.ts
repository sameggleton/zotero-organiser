import { Taxonomy } from '../core/taxonomy.js';
import { Candidate } from './types.js';

export class HybridRanker {
  private taxonomy: Taxonomy;

  constructor(taxonomy: Taxonomy) {
    this.taxonomy = taxonomy;
  }

  /**
   * Computes lexical overlap scores between document text and taxonomy tag definitions.
   */
  public lexicalScores(document: string): Record<string, number> {
    const docTokens = this.tokenize(document.toLowerCase());
    const docCounts = new Map<string, number>();
    for (const t of docTokens) {
      docCounts.set(t, (docCounts.get(t) || 0) + 1);
    }

    const rankingTexts = this.taxonomy.rankingTexts();
    const scores: Record<string, number> = {};

    for (const [tag, text] of Object.entries(rankingTexts)) {
      const tagTokens = this.tokenize(text.toLowerCase());
      if (tagTokens.length === 0) {
        scores[tag] = 0;
        continue;
      }

      let matchCount = 0;
      for (const token of tagTokens) {
        if (docCounts.has(token)) {
          matchCount += 1;
        }
      }
      scores[tag] = matchCount / Math.sqrt(tagTokens.length);
    }

    return scores;
  }

  /**
   * Ranks taxonomy candidates combining dense vector similarities and lexical scores.
   */
  public rank(
    document: string,
    denseScores: Record<string, number> = {},
    denseTopK = 24,
    lexicalTopK = 12,
    perNamespaceK = 3
  ): Candidate[] {
    const lexical = this.lexicalScores(document);
    const allTags = this.taxonomy.classifierTags();
    const selected = new Map<string, Set<string>>();

    const addSource = (tag: string, source: string) => {
      if (!selected.has(tag)) {
        selected.set(tag, new Set());
      }
      selected.get(tag)!.add(source);
    };

    // Top dense
    const sortedDense = Object.entries(denseScores)
      .filter(([tag]) => allTags.has(tag))
      .sort((a, b) => b[1] - a[1])
      .slice(0, denseTopK);

    for (const [tag] of sortedDense) {
      addSource(tag, 'dense');
    }

    // Top lexical
    const sortedLexical = Object.entries(lexical)
      .filter(([tag, score]) => allTags.has(tag) && score > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, lexicalTopK);

    for (const [tag] of sortedLexical) {
      addSource(tag, 'lexical');
    }

    // Per namespace coverage
    const namespaces = this.taxonomy.classifier.semantic_namespaces.length > 0
      ? this.taxonomy.classifier.semantic_namespaces
      : Object.keys(this.taxonomy.namespaces);

    for (const ns of namespaces) {
      const nsScores = Object.entries(denseScores)
        .filter(([tag]) => tag.startsWith(`${ns}/`) && allTags.has(tag))
        .sort((a, b) => b[1] - a[1])
        .slice(0, perNamespaceK);

      for (const [tag] of nsScores) {
        addSource(tag, 'namespace');
      }
    }

    // Combine into candidate list
    const candidates: Candidate[] = [];
    for (const [tag, sources] of selected.entries()) {
      candidates.push({
        tag,
        denseScore: denseScores[tag] || 0,
        lexicalScore: lexical[tag] || 0,
        sources,
      });
    }

    // Sort by dense then lexical then tag name
    return candidates.sort((a, b) => {
      if (b.denseScore !== a.denseScore) return b.denseScore - a.denseScore;
      if (b.lexicalScore !== a.lexicalScore) return b.lexicalScore - a.lexicalScore;
      return a.tag.localeCompare(b.tag);
    });
  }

  private tokenize(text: string): string[] {
    const matches = text.match(/\b[a-zA-Z0-9_\-]+\b/g);
    if (!matches) return [];
    // Filter out common stopwords
    const stopwords = new Set([
      'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'this', 'that'
    ]);
    return matches.filter((w) => w.length > 2 && !stopwords.has(w));
  }
}
