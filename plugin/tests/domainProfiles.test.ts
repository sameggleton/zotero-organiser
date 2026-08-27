import { describe, expect, it } from 'vitest';
import {
  combineTaxonomyProfiles,
  DOMAIN_PROFILES,
  getDomainProfile,
} from '../src/profiles/domainProfiles.js';
import { parseTaxonomy } from '../src/core/taxonomy.js';

describe('Domain Profiles', () => {
  it('contains all 25 required domain profiles', () => {
    expect(DOMAIN_PROFILES.length).toBe(25);
    const expectedProfiles = [
      'general-scholar',
      'mathematics-statistics',
      'computer-information-sciences',
      'physics-astronomy',
      'chemistry-molecular-sciences',
      'biological-sciences',
      'biomedical-clinical-sciences',
      'health-sciences',
      'agricultural-veterinary-food',
      'earth-atmospheric-ocean',
      'environmental-sustainability',
      'engineering-technology',
      'built-environment-architecture',
      'psychology-cognitive-sciences',
      'economics',
      'business-management-organisations',
      'society-politics-human-geography',
      'education-learning-sciences',
      'law-criminology-justice',
      'language-communication-culture',
      'literature-writing',
      'history-heritage-archaeology',
      'philosophy-ethics-religious',
      'creative-arts-design',
      'indigenous-studies',
    ];

    for (const id of expectedProfiles) {
      const found = DOMAIN_PROFILES.find((p) => p.id === id);
      expect(found).toBeDefined();
      expect(found!.name).toBeTruthy();
      expect(found!.category).toBeTruthy();
      expect(found!.description).toBeTruthy();
      expect(found!.sampleTags.length).toBeGreaterThanOrEqual(3);
    }
  });

  it('ensures each individual domain profile is a valid parseable taxonomy', () => {
    for (const profile of DOMAIN_PROFILES) {
      const yamlStr = combineTaxonomyProfiles([profile.id]);
      const parsed = parseTaxonomy(yamlStr);

      expect(parsed.version).toBeTruthy();
      expect(parsed.namespaces).toHaveProperty('status');
      expect(parsed.namespaces).toHaveProperty('priority');
      expect(parsed.namespaces).toHaveProperty('role');
      expect(parsed.namespaces).toHaveProperty('topic');
      expect(parsed.namespaces).toHaveProperty('system');
      expect(parsed.namespaces).toHaveProperty('method');

      const tags = parsed.tags();
      expect(tags.size).toBeGreaterThan(10);
      const classifierTags = parsed.classifierTags();
      expect(classifierTags.size).toBeGreaterThan(5);
    }
  });

  it('getDomainProfile finds profiles by ID or name case-insensitively', () => {
    expect(getDomainProfile('physics-astronomy')?.name).toBe('Physics & Astronomy');
    expect(getDomainProfile('Physics & Astronomy')?.id).toBe('physics-astronomy');
    expect(getDomainProfile('computer-information-sciences')?.name).toBe('Computer & Information Sciences');
    expect(getDomainProfile('non-existent')).toBeUndefined();
  });

  it('combines two domain profiles (Physics & Astronomy + Computer & Info Sciences)', () => {
    const combinedYaml = combineTaxonomyProfiles(['physics-astronomy', 'computer-information-sciences']);
    const taxonomy = parseTaxonomy(combinedYaml);

    expect(taxonomy.version).toBe('1.0.0');
    expect(taxonomy.description).toContain('Physics & Astronomy');
    expect(taxonomy.description).toContain('Computer & Information Sciences');

    const classifierTags = taxonomy.classifierTags();

    // Physics tags
    expect(classifierTags.has('topic/quantum-physics')).toBe(true);
    expect(classifierTags.has('topic/condensed-matter')).toBe(true);
    expect(classifierTags.has('system/quantum-devices')).toBe(true);

    // CS tags
    expect(classifierTags.has('topic/machine-learning')).toBe(true);
    expect(classifierTags.has('topic/algorithms')).toBe(true);

    // Dynamic max_tags scaled
    expect(taxonomy.namespaces.topic.max_tags).toBeGreaterThanOrEqual(3);
  });

  it('combines three domain profiles (Biological Sciences + Chemistry & Molecular Sciences + General Scholar)', () => {
    const combinedYaml = combineTaxonomyProfiles(['biological-sciences', 'chemistry-molecular-sciences', 'general-scholar']);
    const taxonomy = parseTaxonomy(combinedYaml);

    const classifierTags = taxonomy.classifierTags();

    // Biology
    expect(classifierTags.has('topic/cell-biology')).toBe(true);
    expect(classifierTags.has('topic/genetics')).toBe(true);

    // Chemistry
    expect(classifierTags.has('topic/organic-chemistry')).toBe(true);
    expect(classifierTags.has('topic/inorganic-chemistry')).toBe(true);

    // General Scholar
    expect(classifierTags.has('role/empirical')).toBe(true);
    expect(classifierTags.has('method/experiment')).toBe(true);
  });

  it('combines all 25 profiles seamlessly into a comprehensive master taxonomy', () => {
    const allIds = DOMAIN_PROFILES.map((p) => p.id);
    const combinedYaml = combineTaxonomyProfiles(allIds);
    const taxonomy = parseTaxonomy(combinedYaml);

    expect(taxonomy.schemaVersion).toBe(1);
    expect(taxonomy.version).toBe('1.0.0');

    // 6 Namespaces
    expect(Object.keys(taxonomy.namespaces)).toEqual(['status', 'priority', 'role', 'topic', 'system', 'method']);

    const allTags = taxonomy.tags();
    expect(allTags.size).toBeGreaterThanOrEqual(200);

    const classifierTags = taxonomy.classifierTags();
    expect(classifierTags.size).toBeGreaterThanOrEqual(180);
  });
});
