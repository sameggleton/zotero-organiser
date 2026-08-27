import { describe, expect, it } from 'vitest';
import { computeDocumentVector, extractDocumentVector } from '../src/core/document.js';

describe('Document Vector Generation', () => {
  it('generates a zero vector for empty or whitespace text', () => {
    const v1 = computeDocumentVector('');
    const v2 = computeDocumentVector('   ');
    expect(v1.length).toBe(64);
    expect(v1.every((x) => x === 0)).toBe(true);
    expect(v2.every((x) => x === 0)).toBe(true);
  });

  it('generates an L2-normalized vector for non-empty text', () => {
    const text = 'Deep learning for computer vision and image classification';
    const vec = computeDocumentVector(text, 64);

    expect(vec.length).toBe(64);

    const normSq = vec.reduce((sum, x) => sum + x * x, 0);
    expect(normSq).toBeCloseTo(1.0, 5);
  });

  it('produces high cosine similarity for semantically identical or near-identical texts', () => {
    const textA = 'Machine learning neural networks transformer models';
    const textB = 'Transformer neural models machine learning';

    const vecA = computeDocumentVector(textA, 64);
    const vecB = computeDocumentVector(textB, 64);

    // Cosine similarity for normalized vectors is simply dot product
    const dot = vecA.reduce((sum, val, idx) => sum + val * vecB[idx], 0);
    expect(dot).toBeGreaterThan(0.85);

    // Completely identical terms have similarity ~ 1.0
    const textC = 'Machine learning transformer neural models';
    const vecC = computeDocumentVector(textC, 64);
    const dotIdentical = vecB.reduce((sum, val, idx) => sum + val * vecC[idx], 0);
    expect(dotIdentical).toBeCloseTo(1.0, 4);
  });

  it('produces low cosine similarity for unrelated texts', () => {
    const textA = 'Quantum computing qubits entanglement superposition algorithms';
    const textB = 'Medieval history Byzantine Empire feudalism crusades';

    const vecA = computeDocumentVector(textA, 64);
    const vecB = computeDocumentVector(textB, 64);

    const dot = vecA.reduce((sum, val, idx) => sum + val * vecB[idx], 0);
    expect(dot).toBeLessThan(0.4);
  });

  it('extracts document vector from ItemData or item object', () => {
    const itemData = {
      key: 'TEST1',
      version: 1,
      itemType: 'journalArticle',
      title: 'Graph Convolutional Networks',
      abstractNote: 'We present a scalable approach for semi-supervised learning on graph-structured data.',
      publicationTitle: 'ICLR',
      tags: ['topic/computation'],
    };

    const vec = extractDocumentVector(itemData, 64);
    expect(vec.length).toBe(64);
    const normSq = vec.reduce((sum, x) => sum + x * x, 0);
    expect(normSq).toBeCloseTo(1.0, 5);
  });
});
