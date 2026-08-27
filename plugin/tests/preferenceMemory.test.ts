import { describe, expect, it } from 'vitest';
import { PreferenceMemory } from '../src/classifier/preferenceMemory.js';

describe('PreferenceMemory (Tier 1)', () => {
  it('computes zero residual when memory is empty', () => {
    const memory = new PreferenceMemory();
    const docVector = [1.0, 0.0, 0.0];
    const { residual, posSim, negSim } = memory.computeResidual(docVector, 'topic/computation');

    expect(residual).toBe(0);
    expect(posSim).toBe(0);
    expect(negSim).toBe(0);
  });

  it('handles empty or zero-length document vectors gracefully', () => {
    const memory = new PreferenceMemory();
    memory.addExemplar({
      itemKey: 'ITEM1',
      tag: 'topic/computation',
      vector: [1.0, 0.0],
      label: 'positive',
      timestamp: new Date().toISOString(),
    });

    const res1 = memory.computeResidual([], 'topic/computation');
    expect(res1.residual).toBe(0);

    const res2 = memory.computeResidual(null as any, 'topic/computation');
    expect(res2.residual).toBe(0);
  });

  it('boosts candidate score when positive exemplars are close in embedding space', () => {
    const memory = new PreferenceMemory({ alpha: 0.15, beta: 0.15, maxResidual: 0.2 });
    
    // Add positive exemplar for topic/computation
    memory.addExemplar({
      itemKey: 'ITEM1',
      tag: 'topic/computation',
      vector: [1.0, 0.0, 0.0],
      label: 'positive',
      timestamp: new Date().toISOString(),
    });

    const docVector = [0.95, 0.05, 0.0]; // close to positive exemplar
    const { residual, posSim, negSim } = memory.computeResidual(docVector, 'topic/computation');

    expect(posSim).toBeGreaterThan(0.9);
    expect(negSim).toBe(0);
    expect(residual).toBeGreaterThan(0.1);
  });

  it('penalizes candidate score when negative exemplars are close in embedding space', () => {
    const memory = new PreferenceMemory({ alpha: 0.15, beta: 0.15, maxResidual: 0.2 });
    
    // Add negative (rejected) exemplar for topic/computation
    memory.addExemplar({
      itemKey: 'ITEM2',
      tag: 'topic/computation',
      vector: [0.0, 1.0, 0.0],
      label: 'negative',
      timestamp: new Date().toISOString(),
    });

    const docVector = [0.0, 0.98, 0.02]; // close to negative exemplar
    const { residual, posSim, negSim } = memory.computeResidual(docVector, 'topic/computation');

    expect(negSim).toBeGreaterThan(0.9);
    expect(posSim).toBe(0);
    expect(residual).toBeLessThan(-0.1);
  });

  it('strictly bounds the residual within [-maxResidual, +maxResidual]', () => {
    const maxBound = 0.15;
    const memory = new PreferenceMemory({ alpha: 1.0, beta: 1.0, maxResidual: maxBound });

    memory.addExemplar({
      itemKey: 'ITEM3',
      tag: 'role/review',
      vector: [1.0, 1.0, 1.0],
      label: 'positive',
      timestamp: new Date().toISOString(),
    });

    const docVector = [1.0, 1.0, 1.0];
    const { residual } = memory.computeResidual(docVector, 'role/review');

    expect(residual).toBe(maxBound);
  });

  it('correctly reranks candidate lists', () => {
    const memory = new PreferenceMemory({ alpha: 0.15, beta: 0.15, maxResidual: 0.2 });

    memory.addExemplar({
      itemKey: 'ITEM1',
      tag: 'topic/quantum',
      vector: [1.0, 0.0],
      label: 'positive',
      timestamp: new Date().toISOString(),
    });

    const docVector = [1.0, 0.0];
    const candidates = [
      { tag: 'topic/classical', baseScore: 0.80 },
      { tag: 'topic/quantum', baseScore: 0.75 },
    ];

    const reranked = memory.rerank(docVector, candidates);

    // topic/quantum gets boosted above topic/classical
    expect(reranked[0].tag).toBe('topic/quantum');
    expect(reranked[0].personalizedScore).toBeGreaterThan(0.85);
  });

  it('cleans up opposite exemplar when same itemKey and tag is re-labeled', () => {
    const memory = new PreferenceMemory();

    // First rejected as negative
    memory.addExemplar({
      itemKey: 'ITEM_A',
      tag: 'topic/optics',
      vector: [0.5, 0.5],
      label: 'negative',
      timestamp: new Date().toISOString(),
    });

    expect(memory.getStats().negativeCount).toBe(1);
    expect(memory.getStats().positiveCount).toBe(0);

    // Later accepted as positive
    memory.addExemplar({
      itemKey: 'ITEM_A',
      tag: 'topic/optics',
      vector: [0.5, 0.5],
      label: 'positive',
      timestamp: new Date().toISOString(),
    });

    expect(memory.getStats().negativeCount).toBe(0);
    expect(memory.getStats().positiveCount).toBe(1);
    expect(memory.getExemplars('topic/optics', 'positive').length).toBe(1);
    expect(memory.getExemplars('topic/optics', 'negative').length).toBe(0);
  });

  it('supports removeExemplar and clear', () => {
    const memory = new PreferenceMemory();
    memory.addExemplar({
      itemKey: 'ITEM_1',
      tag: 'topic/ai',
      vector: [1, 0],
      label: 'positive',
      timestamp: new Date().toISOString(),
    });
    memory.addExemplar({
      itemKey: 'ITEM_2',
      tag: 'topic/ai',
      vector: [0, 1],
      label: 'negative',
      timestamp: new Date().toISOString(),
    });

    expect(memory.getAllExemplars().length).toBe(2);

    memory.removeExemplar('ITEM_1', 'topic/ai', 'positive');
    expect(memory.getExemplars('topic/ai', 'positive').length).toBe(0);
    expect(memory.getExemplars('topic/ai', 'negative').length).toBe(1);

    memory.clear();
    expect(memory.getAllExemplars().length).toBe(0);
  });
});
