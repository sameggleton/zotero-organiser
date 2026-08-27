export const DEFAULT_TAXONOMY_YAML = `schema_version: 1
version: "1.2.0"

description: >
  Custom domain taxonomy for Molecular Simulation, Chemical Physics,
  Electrolyte Theory, Polymer Conformation, and Rare-Earth Chemistry.
  Calibrated against empirical research library patterns.

conventions:
  separator: "/"
  canonical_tag_format: "{namespace}/{value}"
  allow_unlisted_values: false
  prefer_precision_over_recall: true
  avoid_metadata_duplication: true
  metadata_fields_not_to_tag:
    - author
    - journal
    - year
    - doi
    - publisher
    - institution
  notes:
    - "Topics describe the substantive scientific phenomena, mechanisms, or physical questions."
    - "Systems describe the physical, chemical, or biological matter investigated."
    - "Methods describe computational algorithms, simulation protocols, and analytical techniques."
    - "Roles describe the primary contribution style and utility of the work in the literature."
    - "Status and priority are human-managed workflow namespaces."

classifier:
  semantic_namespaces:
    - role
    - topic
    - system
    - method
    - type
  workflow_namespaces:
    - status
  human_only_namespaces:
    - priority
  rules:
    - "Never invent a tag not defined in this taxonomy."
    - "Do not tag a concept merely because it is mentioned in passing."
    - "Prefer the most specific applicable canonical tag without adding redundant synonyms."
    - "Do not infer priority or workflow status from paper content."
    - "Use aliases only for recognition/normalisation; always emit the canonical value."

relationships: []

namespaces:

  status:
    description: "Reading and processing workflow state."
    kind: workflow
    classifier_eligible: false
    max_tags: 1
    mutually_exclusive: true
    user_managed:
      - reading
      - read
      - processed
    values:
      needs-triage:
        description: "Item requires human review or candidate tags await confirmation."
        aliases: ["triage", "needs review", "needs-review"]
      to-read:
        description: "Item has been queued into the reading list."
        aliases: ["unread", "to read", "to_read"]
      reading:
        description: "Item is actively being read."
      read:
        description: "Item has been read and understood."
        aliases: ["done"]
      processed:
        description: "Notes or knowledge have been extracted into broader research workflow."

  priority:
    description: "User judgment on importance or revisit priority."
    kind: judgement
    classifier_eligible: false
    max_tags: 2
    values:
      core:
        description: "Essential reference literature central to current projects."
      high:
        description: "Important literature of high relevance."
      revisit:
        description: "Contains specific methods, data, or arguments to revisit later."

  type:
    description: "Form or nature of a primary computational product."
    kind: semantic
    classifier_eligible: true
    max_tags: 1
    values:
      software:
        description: "Introduces, documents, or distributes an open-source software package, toolkit, or library."
        aliases: ["package", "codebase", "library", "toolkit", "program"]
      parameters:
        description: "Force-field parameter files, topology sets, or tabulated interaction tables for simulation."
        aliases: ["force-field parameters", "parameter database", "topology files"]

  role:
    description: "Primary style of scientific contribution and why the paper is useful."
    kind: semantic
    classifier_eligible: true
    max_tags: 3
    values:
      computational:
        description: "Primary contribution is based substantially on computational simulation, modeling, or numerical calculations."
        aliases: ["simulation study", "in silico", "numerical study"]
      experimental:
        description: "Primary contribution is based substantially on laboratory experimental measurements or characterization."
        aliases: ["measurement", "empirical study", "wet lab"]
      review:
        description: "Synthesises an existing body of literature rather than presenting only a narrow result."
        aliases: ["systematic review", "state of the art", "overview", "survey"]
        include: ["narrative review", "critical review"]
        exclude: ["brief background section in a primary research article"]
      theory:
        description: "Develops or substantially extends physical theory, analytical derivations, or conceptual frameworks."
        aliases: ["analytical model", "theoretical framework", "continuum theory"]
      method:
        description: "Introduces or materially develops a new algorithm, protocol, or methodological workflow."
        aliases: ["methodology", "algorithm development", "numerical algorithm"]
      mechanistic:
        description: "Primary value is explaining the physical, molecular, or chemical mechanism underlying an observed phenomenon."
        aliases: ["mechanism", "physical mechanism", "molecular origin"]
      benchmark:
        description: "Systematically compares methods, force fields, sampling schemes, or models against ground truth."
        aliases: ["comparative study", "validation", "benchmark study"]
      dataset:
        description: "Introduces, curates, or benchmarks a reusable structure library, trajectory database, or benchmark dataset."
        aliases: ["benchmark dataset", "data repository"]
      application:
        description: "Applies established modeling methods to investigate a specific target problem."
      perspective:
        description: "Provides an opinion, roadmap, critique, or field-level perspective."
      foundational:
        description: "Historically or conceptually foundational milestone work in the field."

  topic:
    description: "Substantive scientific phenomena, questions, or mechanisms investigated."
    kind: semantic
    classifier_eligible: true
    max_tags: 5
    values:
      electrostatics:
        description: "Electrostatic screening, ionic correlations, dielectric response, polarization, or charge interactions."
        aliases: ["charge interactions", "ionic screening", "dielectric response", "polarization", "screening length", "EDL"]
      underscreening:
        description: "Anomalously long-range screening, non-classical decay of charge correlations, or underscreening in concentrated ionic media."
        aliases: ["anomalous underscreening", "long-range screening", "screening length anomaly", "anomalous screening", "long range decay"]
      solvation:
        description: "Solvation thermodynamics, hydration structure, ion coordination environments, or local chemical environments."
        aliases: ["hydration", "solvation structure", "coordination chemistry", "coordination number", "solvation free energy", "ion pairing", "ion clustering"]
      thermodynamics:
        description: "Free-energy landscapes, phase behavior, solubility, binding affinity, or chemical equilibria."
        aliases: ["free energy", "binding affinity", "phase transitions", "phase equilibria", "partitioning", "PMF"]
      transport-dynamics:
        description: "Diffusion, ionic conductivity, residence times, reaction kinetics, or dynamical heterogeneity."
        aliases: ["diffusion", "conductivity", "charge transport", "kinetics", "residence time", "viscosity", "exchange dynamics"]
      interfaces:
        description: "Interfacial structure, adsorption, solid-liquid interfaces, surface charge, or electric double layers."
        aliases: ["adsorption", "interfacial structure", "surface chemistry", "electric double layer", "surface charge"]
      selectivity:
        description: "Chemical selectivity, separation, rare-earth extraction, molecular recognition, or ligand discrimination."
        aliases: ["extraction", "molecular recognition", "chemical separation", "selective binding", "rare-earth separation", "solvent extraction"]
      polymer-conformation:
        description: "Polymer conformational ensembles, chain statistics, radius of gyration, persistence length, or chain scaling."
        aliases: ["chain statistics", "radius of gyration", "polymer conformation", "persistence length", "chain scaling", "coil-globule transition"]
      parameterisation:
        description: "Force-field parameterisation, fitting, optimization, transferability, or accuracy evaluation."
        aliases: ["force-field", "parameterization", "force field parameterisation", "force field development", "fitting force fields"]
      biomolecular-dynamics:
        description: "Protein folding, conformational dynamics, peptide ensembles, or allosteric transitions."
        aliases: ["conformational dynamics", "protein folding", "peptide structure", "allostery", "structural ensemble", "sequence-function"]
      self-assembly:
        description: "Spontaneous aggregation, micelle/vesicle formation, supramolecular organization, or crystallization."
        aliases: ["aggregation", "micellization", "supramolecular", "clustering"]
      machine-learning:
        description: "Machine learning methodologies, representation learning, surrogate models, contrastive learning, or active learning."
        aliases: ["neural network", "deep learning", "representation learning", "surrogate modeling", "active learning", "contrastive learning"]
      statistical-mechanics:
        description: "Statistical mechanical foundations, ensemble theory, correlation functions, or fluctuation theorems."
        aliases: ["statistical mechanics", "correlation functions", "fluctuation dissipation", "ensemble theory"]

  system:
    description: "Chemical, physical, or biological system substantively studied."
    kind: semantic
    classifier_eligible: true
    max_tags: 4
    values:
      electrolyte:
        description: "Ionic solutions, concentrated salts, aqueous electrolytes, ionic liquids, deep eutectic solvents, or polyelectrolytes."
        aliases: ["aqueous electrolyte", "concentrated electrolyte", "ionic liquid", "salt solution", "brine", "deep eutectic solvent", "polyelectrolyte", "water-in-salt"]
      rare-earth:
        description: "Rare-earth elements, lanthanides, or actinide/lanthanide coordination complexes."
        aliases: ["lanthanide", "rare earth", "Ln", "REE", "lanthanides", "rare earths", "trivalent lanthanides"]
      polymer:
        description: "Synthetic polymers, macromolecular melts, crosslinked gels, polymer electrolytes, or block copolymers."
        aliases: ["macromolecule", "polymer melt", "hydrogel", "block copolymer", "polymer electrolyte"]
      aqueous:
        description: "Water, aqueous mixtures, or systems where water solvent structure is central."
        aliases: ["water", "aqueous solution", "liquid water", "ice"]
      mineral:
        description: "Minerals, clay surfaces, oxides, geocatalysts, or rock-water interfaces."
        aliases: ["mineral surface", "clays", "mica", "silica", "metal oxide", "calcite"]
      protein:
        description: "Proteins, enzymes, peptide complexes, or antibodies."
        aliases: ["enzyme", "protein complex", "globular protein", "membrane protein"]
      peptide:
        description: "Short peptides, polypeptides, or intrinsically disordered peptide chains."
        aliases: ["polypeptide", "oligopeptide"]
      membrane:
        description: "Lipid bilayers, biological membranes, synthetic filtration membranes, or vesicles."
        aliases: ["lipid bilayer", "phospholipid", "vesicle", "membrane interface"]
      nanomaterial:
        description: "Nanoparticles, 2D materials, graphene, carbon nanotubes, metal-organic frameworks (MOFs), or electrode surfaces."
        aliases: ["graphene", "nanoparticle", "MOF", "carbon nanotube", "electrode surface", "surface"]
      small-molecule:
        description: "Small organic molecules, ligands, extractants, drug candidates, or organic solvents."
        aliases: ["ligand", "extractant", "drug molecule", "organic solvent"]

  method:
    description: "Computational, analytical, and experimental methods substantively used or evaluated."
    kind: semantic
    classifier_eligible: true
    max_tags: 4
    values:
      molecular-dynamics:
        description: "Classical atomistic or all-atom molecular dynamics simulations."
        aliases: ["MD", "all-atom MD", "classical MD"]
      ab-initio-md:
        description: "First-principles or ab initio molecular dynamics simulations."
        aliases: ["AIMD", "first-principles MD", "Car-Parrinello", "ab initio molecular dynamics"]
      electronic-structure:
        description: "Density functional theory (DFT) or quantum-chemical electronic structure calculations."
        aliases: ["DFT", "density functional theory", "quantum chemistry", "ab initio", "Hartree-Fock"]
      enhanced-sampling:
        description: "Advanced sampling techniques like metadynamics, umbrella sampling, replica exchange, or transition path sampling."
        aliases: ["metadynamics", "umbrella sampling", "replica exchange", "REMD", "accelerated MD", "well-tempered metadynamics"]
      free-energy-calculation:
        description: "Alchemical free energy perturbation (FEP), thermodynamic integration (TI), or potential of mean force (PMF) methods."
        aliases: ["FEP", "thermodynamic integration", "TI", "PMF", "free energy perturbation", "BAR", "MBAR"]
      graph-neural-network:
        description: "Graph neural networks, message-passing neural networks, or equivariant molecular graph models."
        aliases: ["GNN", "graph neural network", "EGNN", "SchNet", "DimeNet", "message passing neural network", "MPNN"]
      ml-potential:
        description: "Machine-learned interatomic potentials, neural network force fields, or equivariant GNN potentials."
        aliases: ["machine learning potential", "neural network potential", "ML force field", "NNP", "MACE", "NequIP", "Allegro"]
      monte-carlo:
        description: "Monte Carlo, grand canonical Monte Carlo (GCMC), or stochastic sampling."
        aliases: ["MC", "GCMC", "Monte Carlo simulation"]
      coarse-grained:
        description: "Coarse-grained modeling, implicit solvent schemes, or mesoscale particle models."
        aliases: ["CG", "coarse-grained MD", "Martini", "dissipative particle dynamics", "DPD", "coarse-grained simulation"]
      spectroscopy:
        description: "Experimental or simulated spectroscopy (IR, Raman, NMR, SAXS/WAXS, X-ray scattering)."
        aliases: ["infrared spectroscopy", "IR", "NMR", "Raman", "SAXS", "WAXS", "X-ray scattering", "spectroscopic analysis"]
`;
