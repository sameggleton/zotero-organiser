import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT_DIR / "examples" / "taxonomies" / "profiles"

PROFILE_METADATA = {
    "general-scholar": {
        "name": "General Scholar",
        "category": "Interdisciplinary & General",
        "icon": "",
        "subdomains": ["Research Methodology", "Scholarly Communication", "Higher Education", "Open Science"],
        "sampleTags": ["role/empirical", "role/review", "topic/research-design", "method/survey", "topic/open-science"]
    },
    "mathematics-statistics": {
        "name": "Mathematics & Statistics",
        "category": "Mathematical Sciences",
        "icon": "",
        "subdomains": ["Pure Mathematics", "Applied Mathematics", "Statistics", "Probability", "Optimisation"],
        "sampleTags": ["topic/algebra", "topic/analysis", "topic/geometry-topology", "topic/probability", "topic/statistics"]
    },
    "computer-information-sciences": {
        "name": "Computer & Information Sciences",
        "category": "Information & Computing",
        "icon": "",
        "subdomains": ["Artificial Intelligence", "Machine Learning", "Software Engineering", "Distributed Systems", "Cybersecurity"],
        "sampleTags": ["topic/machine-learning", "topic/artificial-intelligence", "topic/algorithms", "topic/software-engineering", "topic/distributed-systems"]
    },
    "physics-astronomy": {
        "name": "Physics & Astronomy",
        "category": "Physical Sciences",
        "icon": "",
        "subdomains": ["Quantum Physics", "Condensed Matter", "Astrophysics & Space", "Particle & Nuclear", "Optics & Lasers"],
        "sampleTags": ["topic/quantum-physics", "topic/condensed-matter", "topic/particle-physics", "topic/astrophysics", "topic/optics"]
    },
    "chemistry-molecular-sciences": {
        "name": "Chemistry & Molecular Sciences",
        "category": "Chemical Sciences",
        "icon": "",
        "subdomains": ["Organic Chemistry", "Inorganic & Materials", "Physical & Theoretical", "Computational Chemistry", "Electrochemistry"],
        "sampleTags": ["topic/organic-chemistry", "topic/inorganic-chemistry", "topic/physical-chemistry", "topic/computational-chemistry", "topic/electrochemistry"]
    },
    "biological-sciences": {
        "name": "Biological Sciences",
        "category": "Life Sciences",
        "icon": "",
        "subdomains": ["Molecular & Cell Biology", "Genetics & Genomics", "Microbiology & Virology", "Evolution & Ecology", "Bioinformatics"],
        "sampleTags": ["topic/cell-biology", "topic/genetics", "topic/microbiology", "topic/evolution", "topic/bioinformatics"]
    },
    "biomedical-clinical-sciences": {
        "name": "Biomedical & Clinical Sciences",
        "category": "Medical & Clinical",
        "icon": "",
        "subdomains": ["Neuroscience", "Immunology & Cancer", "Pharmacology & Therapeutics", "Pathology & Diagnostics", "Metabolism"],
        "sampleTags": ["topic/neuroscience", "topic/immunology", "topic/cancer", "topic/pharmacology", "topic/pathology"]
    },
    "health-sciences": {
        "name": "Health Sciences",
        "category": "Public & Allied Health",
        "icon": "",
        "subdomains": ["Epidemiology & Public Health", "Health Services", "Nursing", "Allied Health & Rehab", "Exercise Science"],
        "sampleTags": ["topic/epidemiology", "topic/public-health", "topic/health-services", "topic/nursing", "topic/health-policy"]
    },
    "agricultural-veterinary-food": {
        "name": "Agricultural, Veterinary & Food Sciences",
        "category": "Agricultural & Veterinary",
        "icon": "",
        "subdomains": ["Agronomy & Soil", "Crop Science", "Animal Production", "Food Science", "Veterinary Medicine"],
        "sampleTags": ["topic/agronomy", "topic/crop-science", "topic/animal-science", "topic/food-science", "topic/veterinary-science"]
    },
    "earth-atmospheric-ocean": {
        "name": "Earth, Atmospheric & Ocean Sciences",
        "category": "Earth & Environmental",
        "icon": "",
        "subdomains": ["Geology & Tectonics", "Geophysics & Geochemistry", "Atmospheric Science", "Oceanography & Marine", "Climate Science"],
        "sampleTags": ["topic/geology", "topic/geophysics", "topic/atmospheric-science", "topic/oceanography", "topic/climate-science"]
    },
    "environmental-sustainability": {
        "name": "Environmental & Sustainability Sciences",
        "category": "Earth & Environmental",
        "icon": "",
        "subdomains": ["Ecology & Biodiversity", "Conservation Biology", "Pollution & Ecotoxicology", "Sustainability & LCA", "Environmental Policy"],
        "sampleTags": ["topic/ecology", "topic/conservation", "topic/biodiversity", "topic/sustainability", "topic/environmental-management"]
    },
    "engineering-technology": {
        "name": "Engineering & Technology",
        "category": "Engineering & Tech",
        "icon": "",
        "subdomains": ["Electrical & Electronics", "Mechanical & Aerospace", "Chemical Engineering", "Civil & Structural", "Robotics & Control"],
        "sampleTags": ["topic/electrical-engineering", "topic/mechanical-engineering", "topic/chemical-engineering", "topic/robotics", "topic/materials-engineering"]
    },
    "built-environment-architecture": {
        "name": "Built Environment, Architecture & Planning",
        "category": "Built Environment",
        "icon": "",
        "subdomains": ["Architecture", "Urban & Regional Planning", "Building Science", "Urban Design & Housing", "Sustainable Design"],
        "sampleTags": ["topic/architecture", "topic/urban-planning", "topic/building-science", "topic/sustainable-design", "topic/housing"]
    },
    "psychology-cognitive-sciences": {
        "name": "Psychology & Cognitive Sciences",
        "category": "Behavioral Sciences",
        "icon": "",
        "subdomains": ["Cognitive Psychology", "Behavioral Psychology", "Cognitive Neuroscience", "Mental Health", "Decision Making"],
        "sampleTags": ["topic/cognition", "topic/behaviour", "topic/cognitive-neuroscience", "topic/mental-health", "topic/decision-making"]
    },
    "economics": {
        "name": "Economics",
        "category": "Economic Sciences",
        "icon": "",
        "subdomains": ["Econometrics", "Macroeconomics", "Microeconomics", "Labour Economics", "Behavioural Economics"],
        "sampleTags": ["topic/econometrics", "topic/macroeconomics", "topic/microeconomics", "topic/labour-economics", "topic/behavioural-economics"]
    },
    "business-management-organisations": {
        "name": "Business, Management & Organisations",
        "category": "Business & Management",
        "icon": "",
        "subdomains": ["Finance & Banking", "Accounting & Audit", "Management & Leadership", "Marketing", "Strategy & Innovation"],
        "sampleTags": ["topic/finance", "topic/management", "topic/marketing", "topic/strategy", "topic/entrepreneurship"]
    },
    "society-politics-human-geography": {
        "name": "Society, Politics & Human Geography",
        "category": "Social Sciences",
        "icon": "",
        "subdomains": ["Sociology", "Political Science", "Public Policy", "Anthropology", "Human Geography"],
        "sampleTags": ["topic/sociology", "topic/political-science", "topic/public-policy", "topic/anthropology", "topic/human-geography"]
    },
    "education-learning-sciences": {
        "name": "Education & Learning Sciences",
        "category": "Education",
        "icon": "",
        "subdomains": ["Pedagogy & Teaching", "Curriculum Design", "Educational Technology", "Assessment & Testing", "Higher Education"],
        "sampleTags": ["topic/pedagogy", "topic/curriculum", "topic/learning", "topic/educational-technology", "topic/higher-education"]
    },
    "law-criminology-justice": {
        "name": "Law, Criminology & Justice",
        "category": "Law & Justice",
        "icon": "",
        "subdomains": ["Public & Constitutional Law", "Private & Commercial Law", "International Law", "Criminology", "Criminal Justice"],
        "sampleTags": ["topic/public-law", "topic/private-law", "topic/international-law", "topic/criminology", "topic/criminal-justice"]
    },
    "language-communication-culture": {
        "name": "Language, Communication & Culture",
        "category": "Communication & Culture",
        "icon": "",
        "subdomains": ["Linguistics & Phonetics", "Language Studies", "Communication", "Media & Journalism", "Cultural Studies"],
        "sampleTags": ["topic/linguistics", "topic/language", "topic/communication", "topic/media-studies", "topic/cultural-studies"]
    },
    "literature-writing": {
        "name": "Literature & Writing",
        "category": "Humanities & Literature",
        "icon": "",
        "subdomains": ["Literary Studies", "Literary Theory", "Comparative Literature", "Rhetoric", "Creative Writing"],
        "sampleTags": ["topic/literature", "topic/literary-theory", "topic/comparative-literature", "topic/rhetoric", "topic/creative-writing"]
    },
    "history-heritage-archaeology": {
        "name": "History, Heritage & Archaeology",
        "category": "Historical Studies",
        "icon": "",
        "subdomains": ["World & National History", "Archaeology", "Heritage Conservation", "Archival Science", "Material Culture"],
        "sampleTags": ["topic/history", "topic/archaeology", "topic/heritage", "topic/historiography", "topic/material-culture"]
    },
    "philosophy-ethics-religious": {
        "name": "Philosophy, Ethics & Religious Studies",
        "category": "Philosophy & Religion",
        "icon": "",
        "subdomains": ["Analytic & Continental Philosophy", "Normative & Applied Ethics", "Epistemology & Metaphysics", "Logic", "Religious Studies"],
        "sampleTags": ["topic/philosophy", "topic/ethics", "topic/epistemology", "topic/logic", "topic/philosophy-of-science"]
    },
    "creative-arts-design": {
        "name": "Creative Arts & Design",
        "category": "Creative Arts & Design",
        "icon": "",
        "subdomains": ["Visual Arts", "Music & Sound", "Performing Arts & Theatre", "Design Practice", "Creative Research"],
        "sampleTags": ["topic/visual-arts", "topic/music", "topic/performing-arts", "topic/design", "topic/creative-practice"]
    },
    "indigenous-studies": {
        "name": "Indigenous Studies",
        "category": "Indigenous Studies",
        "icon": "",
        "subdomains": ["Indigenous Knowledge & TEK", "Decolonial Methodologies", "Indigenous Health & Wellbeing", "Indigenous Governance", "Language Revitalization"],
        "sampleTags": ["topic/indigenous-knowledge", "topic/indigenous-methodologies", "topic/indigenous-health", "topic/indigenous-governance", "topic/decolonial-research"]
    }
}

def generate_typescript_modules():
    profiles_dict = {}
    for pid, meta in PROFILE_METADATA.items():
        yml_path = PROFILES_DIR / f"{pid}.yml"
        if not yml_path.exists():
            raise FileNotFoundError(f"Missing {yml_path}")
        content = yml_path.read_text(encoding="utf-8")
        profiles_dict[pid] = {
            "id": pid,
            "name": meta["name"],
            "category": meta["category"],
            "description": meta["name"] + " — " + meta["category"],
            "subdomains": meta["subdomains"],
            "sampleTags": meta["sampleTags"],
            "yaml": content
        }

    # Generate plugin/src/taxonomyProfiles.ts
    ts_lines = [
        "import yaml from 'yaml';",
        "import { parseTaxonomy, Taxonomy } from './core/taxonomy.js';",
        "",
        "export interface TaxonomyProfile {",
        "  id: string;",
        "  name: string;",
        "  category: string;",
        "  description: string;",
        "  subdomains: string[];",
        "  sampleTags?: string[];",
        "  yaml: string;",
        "}",
        ""
    ]

    for pid, pdata in profiles_dict.items():
        var_name = pid.upper().replace("-", "_") + "_YAML"
        ts_lines.append(f"export const {var_name} = {json.dumps(pdata['yaml'])};")
        ts_lines.append("")

    ts_lines.append("export const TAXONOMY_PROFILES: Record<string, TaxonomyProfile> = {")
    for pid, pdata in profiles_dict.items():
        var_name = pid.upper().replace("-", "_") + "_YAML"
        ts_lines.append(f"  '{pid}': {{")
        ts_lines.append(f"    id: '{pid}',")
        ts_lines.append(f"    name: {json.dumps(pdata['name'])},")
        ts_lines.append(f"    category: {json.dumps(pdata['category'])},")
        ts_lines.append(f"    description: {json.dumps(pdata['description'])},")
        ts_lines.append(f"    subdomains: {json.dumps(pdata['subdomains'])},")
        ts_lines.append(f"    sampleTags: {json.dumps(pdata['sampleTags'])},")
        ts_lines.append(f"    yaml: {var_name},")
        ts_lines.append("  },")
    ts_lines.append("};")
    ts_lines.append("")

    # Add combineTaxonomyProfiles implementation
    ts_lines.append("""
function deduplicateStrings(arr: string[]): string[] {
  const seen = new Set<string>();
  const res: string[] = [];
  for (const s of arr) {
    const trimmed = (s || '').trim();
    if (trimmed && !seen.has(trimmed.toLowerCase())) {
      seen.add(trimmed.toLowerCase());
      res.push(trimmed);
    }
  }
  return res;
}

export function combineTaxonomyProfiles(profileIds: string[]): string {
  const cleanIds = deduplicateStrings(profileIds);
  if (cleanIds.length === 0) {
    cleanIds.push('general-scholar');
  }

  const selectedProfiles = cleanIds
    .map((id) => TAXONOMY_PROFILES[id])
    .filter((p): p is TaxonomyProfile => Boolean(p));

  if (selectedProfiles.length === 0) {
    selectedProfiles.push(TAXONOMY_PROFILES['general-scholar']);
  }

  if (selectedProfiles.length === 1) {
    return selectedProfiles[0].yaml;
  }

  const parsedTaxonomies = selectedProfiles.map((p) => {
    try {
      return parseTaxonomy(p.yaml);
    } catch (e) {
      const doc = yaml.parse(p.yaml);
      return doc as any;
    }
  });

  const mergedNamespaces: Record<string, any> = {};
  const mergedDescription = `Unified Multi-Domain Taxonomy combined from ${selectedProfiles.length} profiles: ${selectedProfiles.map((p) => p.name).join(', ')}.`;

  const mergedConventions = {
    separator: '/',
    canonical_tag_format: '{namespace}/{value}',
    allow_unlisted_values: false,
    prefer_precision_over_recall: true,
    avoid_metadata_duplication: true,
    metadata_fields_not_to_tag: ['author', 'journal', 'year', 'doi', 'publisher', 'institution'],
    notes: [
      'Collections/folders organize projects; tags reflect intrinsic domain content.',
      'Role describes contribution style or epistemic purpose in the literature.',
      'Topic describes substantive domain questions, phenomena, or theories.',
      'System describes the physical, biological, conceptual, or social entity investigated.',
      'Method describes specific investigative techniques, protocols, or models.',
      'Status and priority are human-managed workflow namespaces.',
    ],
  };

  const mergedClassifier = {
    semantic_namespaces: ['role', 'topic', 'system', 'method'],
    workflow_namespaces: ['status'],
    human_only_namespaces: ['priority'],
    rules: [
      'Never invent a tag not defined in this taxonomy.',
      'Do not tag a concept merely because it is mentioned in passing.',
      'Prefer the most specific applicable canonical tag without adding redundant synonyms.',
      'Do not infer priority or reading status from document content.',
      'Use aliases only for recognition and normalisation; always emit the canonical tag.',
    ],
  };

  const mergedRelationships: any[] = [];

  const allNsKeys = new Set<string>();
  for (const t of parsedTaxonomies) {
    if (t.namespaces) {
      for (const k of Object.keys(t.namespaces)) {
        allNsKeys.add(k);
      }
    }
  }

  const orderedNsKeys = ['status', 'priority', 'role', 'topic', 'system', 'method'];
  for (const k of allNsKeys) {
    if (!orderedNsKeys.includes(k)) orderedNsKeys.push(k);
  }

  for (const nsKey of orderedNsKeys) {
    if (!allNsKeys.has(nsKey)) continue;

    const baseNs = parsedTaxonomies[0]?.namespaces?.[nsKey] || {};
    const kind = baseNs.kind || (nsKey === 'status' ? 'workflow' : nsKey === 'priority' ? 'judgement' : 'semantic');
    const isSemantic = kind === 'semantic';
    const isWorkflow = kind === 'workflow';

    let maxTags = 2;
    if (nsKey === 'status') maxTags = 1;
    else if (nsKey === 'topic') maxTags = Math.min(6, Math.max(4, selectedProfiles.length + 2));
    else if (nsKey === 'system' || nsKey === 'method') maxTags = Math.min(5, Math.max(3, selectedProfiles.length + 1));
    else if (nsKey === 'role') maxTags = 2;
    else if (nsKey === 'priority') maxTags = 2;

    const mergedValues: Record<string, any> = {};
    const allUserManaged: string[] = [];
    const mergedConstraints: Record<string, any> = {};

    for (const t of parsedTaxonomies) {
      const ns = t.namespaces?.[nsKey];
      if (!ns) continue;

      if (Array.isArray(ns.user_managed)) {
        allUserManaged.push(...ns.user_managed);
      }
      if (ns.constraints && typeof ns.constraints === 'object') {
        Object.assign(mergedConstraints, ns.constraints);
      }

      if (ns.values && typeof ns.values === 'object') {
        for (const [tagKey, tagDef] of Object.entries(ns.values)) {
          if (!mergedValues[tagKey]) {
            mergedValues[tagKey] = {
              description: (tagDef as any).description || '',
              aliases: [...((tagDef as any).aliases || [])],
              include: [...((tagDef as any).include || [])],
              exclude: [...((tagDef as any).exclude || [])],
              classifier_eligible: (tagDef as any).classifier_eligible !== false,
              note: (tagDef as any).note,
            };
          } else {
            const existing = mergedValues[tagKey];
            if (!existing.description && (tagDef as any).description) {
              existing.description = (tagDef as any).description;
            }
            if (Array.isArray((tagDef as any).aliases)) {
              existing.aliases.push(...(tagDef as any).aliases);
            }
            if (Array.isArray((tagDef as any).include)) {
              existing.include.push(...(tagDef as any).include);
            }
            if (Array.isArray((tagDef as any).exclude)) {
              existing.exclude.push(...(tagDef as any).exclude);
            }
          }
        }
      }
    }

    const cleanedValues: Record<string, any> = {};
    for (const [tagKey, val] of Object.entries(mergedValues)) {
      const entry: Record<string, any> = {
        description: val.description || `${tagKey} in ${nsKey} namespace`,
      };
      const cleanedAliases = deduplicateStrings(val.aliases || []);
      if (cleanedAliases.length > 0) {
        entry.aliases = cleanedAliases;
      }
      const cleanedInclude = deduplicateStrings(val.include || []);
      if (cleanedInclude.length > 0) {
        entry.include = cleanedInclude;
      }
      const cleanedExclude = deduplicateStrings(val.exclude || []);
      if (cleanedExclude.length > 0) {
        entry.exclude = cleanedExclude;
      }
      if (val.classifier_eligible === false) {
        entry.classifier_eligible = false;
      }
      if (val.note) {
        entry.note = val.note;
      }
      cleanedValues[tagKey] = entry;
    }

    const nsDescription =
      baseNs.description ||
      (nsKey === 'role'
        ? 'Contribution style or epistemic purpose the work serves in the literature.'
        : nsKey === 'topic'
        ? 'Substantive intellectual themes and domain phenomena.'
        : nsKey === 'system'
        ? 'Entity, model, system, or setting under investigation.'
        : nsKey === 'method'
        ? 'Primary analytical, empirical, computational, or experimental methodology.'
        : '');

    const nsResult: Record<string, any> = {
      description: nsDescription,
      kind,
      classifier_eligible: isSemantic,
      max_tags: maxTags,
    };

    if (baseNs.mutually_exclusive || isWorkflow) {
      nsResult.mutually_exclusive = true;
    }
    if (allUserManaged.length > 0) {
      nsResult.user_managed = deduplicateStrings(allUserManaged);
    }
    if (Object.keys(mergedConstraints).length > 0) {
      nsResult.constraints = mergedConstraints;
    }
    nsResult.values = cleanedValues;

    mergedNamespaces[nsKey] = nsResult;
  }

  const combinedDocument = {
    schema_version: 1,
    version: '1.0.0',
    description: mergedDescription,
    conventions: mergedConventions,
    classifier: mergedClassifier,
    relationships: mergedRelationships,
    namespaces: mergedNamespaces,
  };

  const finalYaml = yaml.stringify(combinedDocument, { indent: 2, lineWidth: 100 });
  parseTaxonomy(finalYaml);
  return finalYaml;
}
""")

    plugin_dir = ROOT_DIR.parent / "zotero-organiser-plugin" / "plugin"
    if not plugin_dir.exists():
      plugin_dir = ROOT_DIR / "plugin"
    out_ts = plugin_dir / "src" / "taxonomyProfiles.ts"
    out_ts.write_text("\n".join(ts_lines), encoding="utf-8")
    print("✓ Generated plugin/src/taxonomyProfiles.ts")

    # Generate plugin/src/profiles/domainProfiles.ts
    domain_ts = """import {
  TAXONOMY_PROFILES,
  TaxonomyProfile,
  combineTaxonomyProfiles,
} from '../taxonomyProfiles.js';
import { parseTaxonomy, RawTaxonomy, Taxonomy } from '../core/taxonomy.js';

export interface DomainProfile {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: string;
  sampleTags: string[];
  subdomains?: string[];
  yaml: string;
}

export const DOMAIN_PROFILES: DomainProfile[] = Object.values(TAXONOMY_PROFILES).map((p) => ({
  id: p.id,
  name: p.name,
  category: p.category,
  description: p.description,
  icon: '',
  sampleTags: p.sampleTags || [],
  subdomains: p.subdomains,
  yaml: p.yaml,
}));

export function getDomainProfile(id: string): DomainProfile | undefined {
  return DOMAIN_PROFILES.find((p) => p.id === id || p.name.toLowerCase() === id.toLowerCase());
}

export { combineTaxonomyProfiles };
"""
    out_domain = plugin_dir / "src" / "profiles" / "domainProfiles.ts"
    out_domain.write_text(domain_ts, encoding="utf-8")
    print("✓ Generated plugin/src/profiles/domainProfiles.ts")

if __name__ == "__main__":
    generate_typescript_modules()
