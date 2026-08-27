import { describe, expect, it, beforeEach } from 'vitest';
import { ZoteroOrganiser } from '../src/index.js';
import { StateStore } from '../src/core/state.js';
import { parseTaxonomy } from '../src/core/taxonomy.js';
import { DEFAULT_TAXONOMY_YAML } from '../src/defaultTaxonomy.js';
import { combineTaxonomyProfiles } from '../src/profiles/domainProfiles.js';

describe('Dynamic Taxonomy Management', () => {
  let organiser: ZoteroOrganiser;

  beforeEach(() => {
    organiser = new ZoteroOrganiser({
      id: 'zotero-organiser@sameggleton.dev',
      version: '1.0.0',
      rootURI: 'chrome://zoteroorganiser/',
    });
  });

  it('initializes with default starter taxonomy', () => {
    expect(organiser.taxonomy.version).toBe('1.2.0');
    expect(organiser.getTaxonomyYaml()).toBe(DEFAULT_TAXONOMY_YAML);
    expect(organiser.taxonomy.classifierTags().has('topic/electrostatics')).toBe(true);
  });

  it('updates taxonomy dynamically via setTaxonomy and saves to StateStore', async () => {
    const physicsAndCsYaml = combineTaxonomyProfiles(['physics-astronomy', 'computer-information-sciences']);

    const res = await organiser.setTaxonomy(physicsAndCsYaml);
    expect(res.success).toBe(true);
    expect(res.error).toBeUndefined();

    // Check active taxonomy on instance
    expect(organiser.taxonomy.version).toBe('1.0.0');
    expect(organiser.getTaxonomyYaml()).toBe(physicsAndCsYaml);
    expect(organiser.taxonomy.classifierTags().has('topic/machine-learning')).toBe(true);
    expect(organiser.taxonomy.classifierTags().has('topic/quantum-physics')).toBe(true);

    // Check StateStore meta persistence
    const savedInStore = await organiser.stateStore.getActiveTaxonomyYaml();
    expect(savedInStore).toBe(physicsAndCsYaml);

    // Check ClassifierEngine updated
    const ranked = organiser.classifier.rankAllCandidates('Machine learning algorithms and quantum physics simulations.');
    expect(ranked.some((r) => r.tag === 'topic/machine-learning')).toBe(true);
    expect(ranked.some((r) => r.tag === 'topic/quantum-physics')).toBe(true);
  });

  it('rejects invalid YAML gracefully and leaves existing taxonomy intact', async () => {
    const originalYaml = organiser.getTaxonomyYaml();
    const originalVersion = organiser.taxonomy.version;

    const invalidYaml = `
schema_version: 1
version: "invalid"
namespaces: {}
`;

    const res = await organiser.setTaxonomy(invalidYaml);
    expect(res.success).toBe(false);
    expect(res.error).toBeTruthy();

    // Existing taxonomy remains unchanged
    expect(organiser.taxonomy.version).toBe(originalVersion);
    expect(organiser.getTaxonomyYaml()).toBe(originalYaml);
  });

  it('StateStore getActiveTaxonomyYaml and setActiveTaxonomyYaml work in memory and query mode', async () => {
    const store = new StateStore();
    expect(await store.getActiveTaxonomyYaml()).toBeNull();

    await store.setActiveTaxonomyYaml(DEFAULT_TAXONOMY_YAML);
    expect(await store.getActiveTaxonomyYaml()).toBe(DEFAULT_TAXONOMY_YAML);
  });
});
