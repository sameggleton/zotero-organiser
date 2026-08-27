# Domain Taxonomy Profiles (Australian FoR Standard)

`zotero-organiser` includes **25 ready-to-use domain taxonomy profiles** aligned with the Australian Government Department of Industry, Science and Resources **Fields of Research (FoR)** standard.

Each profile defines a complete, multi-namespace taxonomy:
- **`role`**: Epistemic and document function (e.g. `role/empirical`, `role/theoretical`, `role/review`).
- **`topic`**: Domain-specific conceptual areas and subjects.
- **`system`**: Domain-specific physical, biological, mathematical, or social objects of study.
- **`method`**: Empirical, analytical, computational, or theoretical methodology.
- **`status`**: Standardized reading/triage lifecycle (`status/needs-triage`, `status/to-read`, `status/reading`, `status/read`, `status/processed`).
- **`priority`**: User judgement levels (`priority/core`, `priority/marginal`).

---

## Profile Catalog

| # | Profile Name | Identifier | File Path | Primary Fields & Subdomains |
|---|---|---|---|---|
| 1 | **General Scholar** | `general-scholar` | [`profiles/general-scholar.yml`](profiles/general-scholar.yml) | Interdisciplinary, Research Design, Open Science, Qualitative/Empirical |
| 2 | **Mathematics & Statistics** | `mathematics-statistics` | [`profiles/mathematics-statistics.yml`](profiles/mathematics-statistics.yml) | Pure & Applied Mathematics, Probability, Statistics, Optimisation |
| 3 | **Computer & Information Sciences** | `computer-information-sciences` | [`profiles/computer-information-sciences.yml`](profiles/computer-information-sciences.yml) | Machine Learning, AI, Algorithms, Software Engineering, Systems |
| 4 | **Physics & Astronomy** | `physics-astronomy` | [`profiles/physics-astronomy.yml`](profiles/physics-astronomy.yml) | Quantum Physics, Condensed Matter, Astrophysics, Particle Physics, Optics |
| 5 | **Chemistry & Molecular Sciences** | `chemistry-molecular-sciences` | [`profiles/chemistry-molecular-sciences.yml`](profiles/chemistry-molecular-sciences.yml) | Organic, Inorganic, Physical, Computational Chemistry, Electrochemistry |
| 6 | **Biological Sciences** | `biological-sciences` | [`profiles/biological-sciences.yml`](profiles/biological-sciences.yml) | Cell Biology, Genetics, Microbiology, Evolution, Bioinformatics |
| 7 | **Biomedical & Clinical Sciences** | `biomedical-clinical-sciences` | [`profiles/biomedical-clinical-sciences.yml`](profiles/biomedical-clinical-sciences.yml) | Neuroscience, Immunology, Cancer, Pharmacology, Pathology |
| 8 | **Health Sciences** | `health-sciences` | [`profiles/health-sciences.yml`](profiles/health-sciences.yml) | Epidemiology, Public Health, Health Services, Nursing, Policy |
| 9 | **Agricultural, Veterinary & Food** | `agricultural-veterinary-food` | [`profiles/agricultural-veterinary-food.yml`](profiles/agricultural-veterinary-food.yml) | Agronomy, Crop Science, Animal Science, Food Science, Veterinary |
| 10 | **Earth, Atmospheric & Ocean** | `earth-atmospheric-ocean` | [`profiles/earth-atmospheric-ocean.yml`](profiles/earth-atmospheric-ocean.yml) | Geology, Geophysics, Oceanography, Climate Science, Meteorology |
| 11 | **Environmental & Sustainability** | `environmental-sustainability` | [`profiles/environmental-sustainability.yml`](profiles/environmental-sustainability.yml) | Ecology, Conservation, Biodiversity, Sustainability, Environmental Management |
| 12 | **Engineering & Technology** | `engineering-technology` | [`profiles/engineering-technology.yml`](profiles/engineering-technology.yml) | Electrical, Mechanical, Chemical, Robotics, Materials Engineering |
| 13 | **Built Environment & Architecture** | `built-environment-architecture` | [`profiles/built-environment-architecture.yml`](profiles/built-environment-architecture.yml) | Architecture, Urban Planning, Building Science, Sustainable Design |
| 14 | **Psychology & Cognitive Sciences** | `psychology-cognitive-sciences` | [`profiles/psychology-cognitive-sciences.yml`](profiles/psychology-cognitive-sciences.yml) | Cognition, Behaviour, Cognitive Neuroscience, Mental Health |
| 15 | **Economics** | `economics` | [`profiles/economics.yml`](profiles/economics.yml) | Econometrics, Macroeconomics, Microeconomics, Labour, Behavioural Economics |
| 16 | **Business & Management** | `business-management-organisations` | [`profiles/business-management-organisations.yml`](profiles/business-management-organisations.yml) | Finance, Management, Marketing, Strategy, Entrepreneurship |
| 17 | **Society, Politics & Geography** | `society-politics-human-geography` | [`profiles/society-politics-human-geography.yml`](profiles/society-politics-human-geography.yml) | Sociology, Political Science, Public Policy, Anthropology, Geography |
| 18 | **Education & Learning Sciences** | `education-learning-sciences` | [`profiles/education-learning-sciences.yml`](profiles/education-learning-sciences.yml) | Pedagogy, Curriculum, Educational Technology, Higher Education |
| 19 | **Law, Criminology & Justice** | `law-criminology-justice` | [`profiles/law-criminology-justice.yml`](profiles/law-criminology-justice.yml) | Public Law, Private Law, International Law, Criminology, Criminal Justice |
| 20 | **Language, Communication & Culture** | `language-communication-culture` | [`profiles/language-communication-culture.yml`](profiles/language-communication-culture.yml) | Linguistics, Communication, Media Studies, Cultural Studies |
| 21 | **Literature & Writing** | `literature-writing` | [`profiles/literature-writing.yml`](profiles/literature-writing.yml) | Literature, Literary Theory, Comparative Literature, Creative Writing |
| 22 | **History, Heritage & Archaeology** | `history-heritage-archaeology` | [`profiles/history-heritage-archaeology.yml`](profiles/history-heritage-archaeology.yml) | History, Archaeology, Heritage, Historiography, Material Culture |
| 23 | **Philosophy, Ethics & Religion** | `philosophy-ethics-religious` | [`profiles/philosophy-ethics-religious.yml`](profiles/philosophy-ethics-religious.yml) | Philosophy, Ethics, Epistemology, Logic, Philosophy of Science |
| 24 | **Creative Arts & Design** | `creative-arts-design` | [`profiles/creative-arts-design.yml`](profiles/creative-arts-design.yml) | Visual Arts, Music, Performing Arts, Design, Creative Practice |
| 25 | **Indigenous Studies** | `indigenous-studies` | [`profiles/indigenous-studies.yml`](profiles/indigenous-studies.yml) | Indigenous Knowledge, Decolonial Research, Indigenous Health & Governance |

---

## Usage

### Using with the Python CLI
```bash
# List all available domain profiles
zotero-organiser taxonomy profiles list

# View the full taxonomy structure of a profile
zotero-organiser taxonomy profiles show computer-information-sciences

# Initialize your library's active taxonomy from a domain profile
zotero-organiser taxonomy init --from examples/taxonomies/profiles/physics-astronomy.yml
```

### Using in the Zotero GUI Plugin
Open Zotero Settings → **Zotero Organiser** → **Profiles** tab. You can select single profiles or combine multiple profiles (e.g. *Computer Science* + *Psychology* + *Indigenous Studies*) to generate a unified, personalized research taxonomy automatically.
