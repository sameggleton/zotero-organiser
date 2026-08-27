import os
import yaml
from pathlib import Path
from zotero_organiser.taxonomy import load_taxonomy, Taxonomy

PROFILES_DATA = [
    {
        "id": "general-scholar",
        "name": "General Scholar",
        "category": "Interdisciplinary & General",
        "description": "Cross-disciplinary profile for general academic literature, research methodology, higher education, and scientific communication.",
        "sampleTags": ["role/empirical", "role/review", "topic/research-design", "method/survey", "topic/open-science"],
        "topics": {
            "research-design": {"desc": "Methodology, experimental design, causal inference, and validity.", "aliases": ["methodology", "study design", "experimental design"]},
            "open-science": {"desc": "Reproducibility, open data, preprints, preregistration, and open access.", "aliases": ["reproducibility", "replication", "open data", "preregistration"]},
            "scholarly-communication": {"desc": "Peer review, scientometrics, academic publishing, and citation dynamics.", "aliases": ["scientometrics", "bibliometrics", "peer review", "publishing"]},
            "science-policy": {"desc": "Research funding, science governance, societal impact, and technology policy.", "aliases": ["research funding", "research policy", "innovation policy"]},
            "research-ethics": {"desc": "Research integrity, human subject protections, dual-use research, and ethical oversight.", "aliases": ["bioethics", "research integrity", "IRB", "academic ethics"]},
            "interdisciplinary-studies": {"desc": "Cross-boundary research, synthesis frameworks, and convergent science.", "aliases": ["multidisciplinary", "transdisciplinary", "convergence"]},
            "higher-education": {"desc": "Academic institutions, doctoral training, university administration, and pedagogy.", "aliases": ["academia", "university", "doctoral education"]},
            "data-infrastructure": {"desc": "Research data management, FAIR principles, archives, and scholarly repositories.", "aliases": ["FAIR data", "data repositories", "research data"]},
        },
        "systems": {
            "academic-institutions": {"desc": "Universities, research institutes, colleges, and scholarly associations.", "aliases": ["university", "institute", "faculty"]},
            "scholarly-literature": {"desc": "Journal articles, preprints, conference proceedings, and monographs.", "aliases": ["literature", "papers", "monographs"]},
            "research-community": {"desc": "Scientists, scholarly networks, peer reviewers, and scientific disciplines.", "aliases": ["researchers", "scholars", "scientific network"]},
            "funding-bodies": {"desc": "National funding agencies, philanthropic foundations, and grant schemes.", "aliases": ["grant agency", "funding agency", "NSF", "ERC"]},
            "research-infrastructure": {"desc": "Shared computing facilities, research laboratories, and institutional repositories.", "aliases": ["facilities", "shared lab", "supercomputer"]},
        },
        "methods": {
            "experiment": {"desc": "Controlled lab, field, or online experimental procedures.", "aliases": ["controlled trial", "lab experiment", "field experiment"]},
            "simulation": {"desc": "Numerical, agent-based, or synthetic computational simulation.", "aliases": ["computational simulation", "agent-based model"]},
            "survey": {"desc": "Questionnaires, stratified sampling, and cross-sectional survey instruments.", "aliases": ["questionnaire", "sample survey", "polling"]},
            "qualitative": {"desc": "Interviews, focus groups, thematic analysis, and ethnographic fieldwork.", "aliases": ["thematic analysis", "interviews", "fieldwork"]},
            "literature-synthesis": {"desc": "Systematic reviews, meta-analyses, and scoping reviews.", "aliases": ["meta-analysis", "systematic review", "scoping review"]},
            "quantitative-analysis": {"desc": "Statistical regression, econometric estimation, and observational data analysis.", "aliases": ["regression", "multivariate analysis", "statistics"]},
        }
    },
    {
        "id": "mathematics-statistics",
        "name": "Mathematics & Statistics",
        "category": "Mathematical Sciences",
        "description": "Covers pure and applied mathematics, probability, statistics, optimisation, numerical mathematics and mathematical modelling.",
        "sampleTags": ["topic/algebra", "topic/analysis", "topic/geometry", "topic/probability", "topic/statistics"],
        "topics": {
            "algebra": {"desc": "Abstract algebra, group theory, ring theory, representation theory, and algebraic structures.", "aliases": ["group theory", "ring theory", "representation theory", "lie algebra", "commutative algebra"]},
            "analysis": {"desc": "Real and complex analysis, functional analysis, harmonic analysis, and partial differential equations.", "aliases": ["functional analysis", "harmonic analysis", "complex analysis", "PDEs", "operator theory"]},
            "geometry-topology": {"desc": "Differential geometry, algebraic geometry, manifold theory, and algebraic/differential topology.", "aliases": ["differential geometry", "algebraic geometry", "topology", "riemannian geometry", "manifold"]},
            "probability": {"desc": "Stochastic processes, measure theory, random matrices, martingale theory, and Markov chains.", "aliases": ["stochastic process", "random matrices", "markov chain", "martingale", "brownian motion"]},
            "statistics": {"desc": "Statistical inference, Bayesian statistics, nonparametric estimation, asymptotic theory, and experimental design.", "aliases": ["statistical inference", "bayesian", "nonparametric", "hypothesis testing", "asymptotics"]},
            "optimisation": {"desc": "Convex optimisation, non-convex programming, variational analysis, and combinatorial optimisation.", "aliases": ["convex optimization", "linear programming", "gradient descent", "variational inequalities"]},
            "numerical-methods": {"desc": "Numerical linear algebra, finite element analysis, spectral methods, and error analysis.", "aliases": ["finite element", "numerical analysis", "spectral methods", "discretization"]},
            "mathematical-modelling": {"desc": "Formulation, dynamical systems analysis, and qualitative theory of continuous/discrete models.", "aliases": ["dynamical systems", "bifurcation theory", "compartmental model", "differential equations"]},
            "number-theory-combinatorics": {"desc": "Analytic/algebraic number theory, graph theory, combinatorics, and discrete mathematics.", "aliases": ["number theory", "graph theory", "combinatorics", "discrete mathematics"]},
        },
        "systems": {
            "algebraic-structures": {"desc": "Groups, rings, fields, vector spaces, and category-theoretic objects.", "aliases": ["group", "field", "ring", "category", "manifold"]},
            "dynamical-systems": {"desc": "Continuous and discrete dynamical systems, ODEs, PDEs, and flow maps.", "aliases": ["vector field", "phase space", "flow map"]},
            "stochastic-models": {"desc": "Markov processes, Poisson processes, random graphs, and stochastic differential equations.", "aliases": ["SDE", "markov model", "random graph"]},
            "mathematical-networks": {"desc": "Graphs, complex networks, hypergraphs, and simplicial complexes.", "aliases": ["graph", "network", "simplicial complex"]},
            "discrete-structures": {"desc": "Partitions, lattices, matroids, polytopes, and combinatorial designs.", "aliases": ["polytope", "lattice", "matroid"]},
        },
        "methods": {
            "rigorous-proof": {"desc": "Formal deductive mathematical proof, axiomatic derivation, and lemma verification.", "aliases": ["mathematical proof", "theorem proof", "lemma derivation"]},
            "asymptotic-analysis": {"desc": "Perturbation theory, saddle-point approximation, asymptotic expansion, and boundary layer theory.", "aliases": ["perturbation theory", "asymptotic expansion", "WKB"]},
            "numerical-simulation": {"desc": "Finite difference/element simulations, matrix solvers, and root-finding iterations.", "aliases": ["FEM", "FDM", "numerical solver"]},
            "monte-carlo-simulation": {"desc": "MCMC, Gibbs sampling, Metropolis-Hastings, and importance sampling algorithms.", "aliases": ["MCMC", "metropolis hastings", "gibbs sampling"]},
            "statistical-inference": {"desc": "Maximum likelihood estimation, generalized linear models, and bootstrap resampling.", "aliases": ["MLE", "GLM", "bootstrap", "cross-validation"]},
            "variational-methods": {"desc": "Calculus of variations, energy minimization, minimax theorems, and convex relaxation.", "aliases": ["calculus of variations", "energy minimization", "convex relaxation"]},
        }
    },
    {
        "id": "computer-information-sciences",
        "name": "Computer & Information Sciences",
        "category": "Information & Computing",
        "description": "Covers computer science, AI, data science, software, information systems and computing infrastructure.",
        "sampleTags": ["topic/machine-learning", "topic/artificial-intelligence", "topic/algorithms", "topic/software-engineering", "topic/distributed-systems"],
        "topics": {
            "machine-learning": {"desc": "Supervised, unsupervised, reinforcement learning, deep architectures, and neural representations.", "aliases": ["deep learning", "neural network", "reinforcement learning", "representation learning", "transformer"]},
            "artificial-intelligence": {"desc": "Knowledge representation, automated reasoning, heuristic search, planning, and multi-agent systems.", "aliases": ["knowledge graph", "automated reasoning", "planning", "agent-based AI", "heuristic search"]},
            "algorithms": {"desc": "Complexity theory, approximation algorithms, randomized algorithms, graph algorithms, and data structures.", "aliases": ["complexity theory", "data structures", "approximation algorithms", "graph algorithms"]},
            "software-engineering": {"desc": "Software architecture, program verification, testing, CI/CD, static analysis, and code synthesis.", "aliases": ["testing", "static analysis", "program verification", "code synthesis", "software architecture"]},
            "distributed-systems": {"desc": "Consensus protocols, cloud computing, edge computing, distributed storage, and microservices.", "aliases": ["cloud computing", "consensus", "paxos", "raft", "microservices", "edge computing"]},
            "cybersecurity": {"desc": "Cryptography, network security, vulnerability analysis, threat modeling, and zero-trust systems.", "aliases": ["cryptography", "zero trust", "threat modeling", "vulnerability", "encryption"]},
            "data-science": {"desc": "Big data analytics, data mining, feature engineering, information retrieval, and knowledge discovery.", "aliases": ["data mining", "information retrieval", "big data", "feature engineering", "RAG"]},
            "human-computer-interaction": {"desc": "User interface design, usability evaluation, interactive computing, and accessibility.", "aliases": ["HCI", "UX", "user interface", "usability", "interaction design"]},
            "computer-vision": {"desc": "Image recognition, object detection, 3D reconstruction, vision-language models, and generative visual AI.", "aliases": ["vision-language", "object detection", "image segmentation", "3D vision"]},
            "natural-language-processing": {"desc": "Large language models, machine translation, syntax parsing, text generation, and speech processing.", "aliases": ["NLP", "LLM", "speech recognition", "machine translation", "text generation"]},
        },
        "systems": {
            "software-systems": {"desc": "Applications, compilers, operating systems, frameworks, and programming runtimes.", "aliases": ["compiler", "runtime", "operating system", "framework", "library"]},
            "distributed-infrastructure": {"desc": "Cloud clusters, Kubernetes, datacenters, peer-to-peer networks, and edge nodes.", "aliases": ["cloud cluster", "kubernetes", "datacenter", "p2p"]},
            "neural-models": {"desc": "Foundation models, convolutional networks, transformers, diffusion models, and GNNs.", "aliases": ["foundation model", "transformer", "diffusion model", "GNN"]},
            "hardware-architectures": {"desc": "GPUs, TPUs, ASICs, neuromorphic chips, and quantum processing units (QPUs).", "aliases": ["GPU", "TPU", "ASIC", "accelerator", "QPU"]},
            "information-networks": {"desc": "The World Wide Web, semantic web, social graphs, and knowledge repositories.", "aliases": ["knowledge base", "social network", "semantic web"]},
        },
        "methods": {
            "algorithmic-design": {"desc": "Algorithm specification, asymptotic complexity proof, and correctness verification.", "aliases": ["algorithm proof", "complexity bound"]},
            "model-training": {"desc": "Backpropagation, gradient descent, hyperparameter tuning, and distributed training.", "aliases": ["training", "fine-tuning", "LoRA", "gradient descent"]},
            "empirical-benchmarking": {"desc": "Standard test suites, ablation studies, latency profiling, and comparative benchmarks.", "aliases": ["benchmark", "ablation", "comparative study"]},
            "formal-verification": {"desc": "Model checking, theorem proving (Coq/Lean), and formal specification validation.", "aliases": ["model checking", "formal proof", "lean", "coq"]},
            "user-study": {"desc": "Task evaluation, controlled usability experiments, cognitive walkthroughs, and telemetry.", "aliases": ["usability test", "controlled study", "user telemetry"]},
        }
    },
    {
        "id": "physics-astronomy",
        "name": "Physics & Astronomy",
        "category": "Physical Sciences",
        "description": "Covers fundamental and applied physical sciences from quantum and condensed-matter physics through particle, nuclear, plasma, optical, astronomical and space sciences.",
        "sampleTags": ["topic/quantum-physics", "topic/condensed-matter", "topic/particle-physics", "topic/astrophysics", "topic/optics"],
        "topics": {
            "quantum-physics": {"desc": "Quantum information, quantum optics, entanglement, quantum foundations, and quantum error correction.", "aliases": ["quantum information", "entanglement", "quantum computing", "qubit", "quantum optics"]},
            "condensed-matter": {"desc": "Superconductivity, topological states, magnetic materials, electronic transport, and 2D materials.", "aliases": ["superconductivity", "topological insulator", "semiconductor", "2D materials", "magnetism"]},
            "particle-physics": {"desc": "Standard model, collider physics, Higgs physics, neutrino oscillations, and beyond-standard-model theory.", "aliases": ["standard model", "collider", "higgs", "neutrino", "dark matter", "QFT"]},
            "nuclear-physics": {"desc": "Nuclear structure, heavy-ion collisions, quark-gluon plasma, and nuclear astrophysics.", "aliases": ["nuclear structure", "heavy ion", "quark gluon plasma", "fission", "fusion"]},
            "optics": {"desc": "Lasers, non-linear optics, photonics, plasmonics, metamaterials, and ultrafast spectroscopy.", "aliases": ["photonics", "laser", "metamaterial", "plasmonics", "nonlinear optics"]},
            "plasma-physics": {"desc": "Magnetic confinement fusion (tokamaks), laser-plasma acceleration, space plasmas, and MHD.", "aliases": ["tokamak", "fusion plasma", "MHD", "plasma acceleration"]},
            "astrophysics": {"desc": "Stellar evolution, compact objects (black holes/neutron stars), galaxies, and gravitational waves.", "aliases": ["black hole", "neutron star", "galaxy", "gravitational wave", "supernova"]},
            "space-science": {"desc": "Cosmology, cosmic microwave background, exoplanetary systems, and solar physics.", "aliases": ["cosmology", "CMB", "exoplanet", "heliophysics", "dark energy"]},
        },
        "systems": {
            "quantum-devices": {"desc": "Superconducting qubits, trapped ions, Rydberg atoms, and photonic circuits.", "aliases": ["qubit", "trapped ion", "rydberg atom", "quantum circuit"]},
            "solid-state-materials": {"desc": "Crystals, thin films, heterostructures, superconductors, and topological matter.", "aliases": ["crystal", "heterostructure", "superconductor", "thin film"]},
            "astrophysical-objects": {"desc": "Black holes, active galactic nuclei (AGN), pulsars, stars, and exoplanets.", "aliases": ["black hole", "pulsar", "star", "exoplanet", "galaxy cluster"]},
            "plasma-confinements": {"desc": "Tokamaks, stellarators, laser targets, and astrophysical accretion disks.", "aliases": ["tokamak", "stellarator", "accretion disk"]},
            "particle-accelerators": {"desc": "Colliders (LHC), synchrotron sources, and underground particle detectors.", "aliases": ["collider", "synchrotron", "LHC", "detector"]},
        },
        "methods": {
            "theoretical-derivation": {"desc": "Quantum field theory calculations, perturbation expansions, and analytical mechanics.", "aliases": ["QFT calculation", "feynman diagram", "analytical derivation"]},
            "astronomical-observation": {"desc": "Radio/optical telescopes, space observatories, spectroscopy, and interferometer imaging.", "aliases": ["telescope", "spectroscopy", "JWST", "interferometry"]},
            "numerical-simulation": {"desc": "N-body gravity, magnetohydrodynamic (MHD), ab initio DFT, and particle-in-cell (PIC).", "aliases": ["N-body", "MHD simulation", "PIC", "DFT"]},
            "laboratory-experiment": {"desc": "Cryogenic measurements, optical setups, beam experiments, and ultrafast laser probes.", "aliases": ["cryogenics", "laser probe", "spectroscopic measurement"]},
            "data-reconstruction": {"desc": "Gravitational-wave parameter estimation, particle track reconstruction, and imaging pipelines.", "aliases": ["event reconstruction", "parameter estimation", "bayesian fit"]},
        }
    },
    {
        "id": "chemistry-molecular-sciences",
        "name": "Chemistry & Molecular Sciences",
        "category": "Chemical Sciences",
        "description": "Covers analytical, inorganic, organic, physical, theoretical, computational, medicinal and macromolecular chemistry.",
        "sampleTags": ["topic/organic-chemistry", "topic/inorganic-chemistry", "topic/physical-chemistry", "topic/computational-chemistry", "topic/electrochemistry"],
        "topics": {
            "organic-chemistry": {"desc": "Total synthesis, reaction methodology, organocatalysis, stereochemistry, and retrosynthesis.", "aliases": ["synthesis", "organocatalysis", "reaction mechanism", "stereochemistry", "retrosynthesis"]},
            "inorganic-chemistry": {"desc": "Coordination complexes, organometallics, bioinorganic chemistry, solid-state chemistry, and f-elements.", "aliases": ["coordination complex", "organometallic", "lanthanide", "transition metal", "MOF"]},
            "physical-chemistry": {"desc": "Chemical thermodynamics, kinetics, reaction dynamics, spectroscopy, and solvation phenomena.", "aliases": ["thermodynamics", "kinetics", "spectroscopy", "solvation", "photochemistry"]},
            "analytical-chemistry": {"desc": "Mass spectrometry, chromatography, NMR spectroscopy, biosensors, and chemical metrology.", "aliases": ["mass spec", "chromatography", "HPLC", "NMR", "biosensor", "sensor"]},
            "computational-chemistry": {"desc": "Electronic structure (DFT), molecular dynamics (MD), force fields, and machine-learned potentials.", "aliases": ["DFT", "molecular dynamics", "quantum chemistry", "ab initio", "force field"]},
            "medicinal-chemistry": {"desc": "Structure-activity relationships (SAR), drug design, pharmacokinetics, and lead optimization.", "aliases": ["SAR", "drug design", "pharmacophore", "lead optimization", "docking"]},
            "polymer-chemistry": {"desc": "Polymer synthesis, macromolecular architectures, living polymerization, and block copolymers.", "aliases": ["polymerization", "macromolecule", "block copolymer", "hydrogel"]},
            "electrochemistry": {"desc": "Electrocatalysis, batteries, fuel cells, redox mechanisms, and electrochemical double layers.", "aliases": ["battery", "electrocatalysis", "fuel cell", "redox", "cyclic voltammetry"]},
        },
        "systems": {
            "molecular-compounds": {"desc": "Small organic molecules, ligands, catalysts, pharmaceuticals, and peptides.", "aliases": ["small molecule", "ligand", "catalyst", "drug"]},
            "coordination-complexes": {"desc": "Transition-metal complexes, lanthanide chelates, and metalloenzymes.", "aliases": ["complex", "chelate", "metallocene"]},
            "macromolecules-polymers": {"desc": "Synthetic polymers, biopolymers, dendrimers, and crosslinked hydrogels.", "aliases": ["polymer", "dendrimer", "gel"]},
            "electrochemical-cells": {"desc": "Battery electrodes, electrolyte solutions, interfaces, and electrochemical cells.", "aliases": ["electrode", "electrolyte", "battery cell"]},
            "surfaces-catalysts": {"desc": "Heterogeneous catalysts, nanoparticle surfaces, MOFs, and thin films.", "aliases": ["heterogeneous catalyst", "MOF", "nanoparticle surface"]},
        },
        "methods": {
            "chemical-synthesis": {"desc": "Bench synthesis, purification (chromatography), crystallization, and reaction optimization.", "aliases": ["synthesis", "purification", "column chromatography", "crystallization"]},
            "spectroscopic-characterisation": {"desc": "NMR, IR, Raman, UV-Vis, EPR, and X-ray photoelectron spectroscopy (XPS).", "aliases": ["NMR", "IR", "Raman", "UV-Vis", "XPS", "spectroscopy"]},
            "xray-crystallography": {"desc": "Single-crystal XRD, powder XRD, and structural refinement.", "aliases": ["XRD", "crystallography", "single crystal"]},
            "mass-spectrometry": {"desc": "ESI-MS, MALDI-TOF, LC-MS/MS, and high-resolution mass spectrometry.", "aliases": ["LC-MS", "ESI-MS", "MALDI", "MS/MS"]},
            "computational-modeling": {"desc": "DFT calculations, all-atom MD simulations, enhanced sampling, and QM/MM.", "aliases": ["DFT", "MD simulation", "QM/MM", "metadynamics"]},
            "electrochemical-measurement": {"desc": "Cyclic voltammetry, electrochemical impedance spectroscopy (EIS), and chronoamperometry.", "aliases": ["cyclic voltammetry", "CV", "EIS", "galvanostatic"]},
        }
    },
    {
        "id": "biological-sciences",
        "name": "Biological Sciences",
        "category": "Life Sciences",
        "description": "Covers fundamental life sciences including molecular and cell biology, genetics, microbiology, evolution, physiology, plant biology, zoology and bioinformatics.",
        "sampleTags": ["topic/cell-biology", "topic/genetics", "topic/microbiology", "topic/evolution", "topic/bioinformatics"],
        "topics": {
            "cell-biology": {"desc": "Organelle function, membrane trafficking, cell division, cytoskeleton, and signal transduction.", "aliases": ["cytoskeleton", "membrane trafficking", "mitosis", "signaling", "autophagy"]},
            "genetics": {"desc": "Genome architecture, epigenetics, gene expression regulation, mutagenesis, and population genetics.", "aliases": ["epigenetics", "gene regulation", "mutation", "transcriptomics", "CRISPR"]},
            "microbiology": {"desc": "Bacterial physiology, virology, fungal biology, host-pathogen interactions, and microbiomes.", "aliases": ["bacterial", "virus", "virology", "microbiome", "fungal", "pathogen"]},
            "evolution": {"desc": "Phylogenetics, speciation, natural selection, adaptation, and evolutionary developmental biology.", "aliases": ["phylogeny", "speciation", "natural selection", "adaptation", "evo-devo"]},
            "physiology": {"desc": "Comparative physiology, cellular homeostasis, organ systems, and electrophysiology.", "aliases": ["homeostasis", "organ system", "electrophysiology", "circadian"]},
            "plant-biology": {"desc": "Photosynthesis, plant genetics, crop physiology, plant pathology, and phytohormone signaling.", "aliases": ["photosynthesis", "plant pathology", "arabidopsis", "phytohormone", "chloroplast"]},
            "zoology": {"desc": "Animal behavior, comparative anatomy, entomology, marine biology, and organismal biology.", "aliases": ["animal behavior", "entomology", "marine biology", "comparative anatomy"]},
            "bioinformatics": {"desc": "Sequence alignment, structural bioinformatics, phylogenomics, and multi-omics integration.", "aliases": ["sequence alignment", "omics", "phylogenomics", "structural bioinformatics", "alphafold"]},
            "structural-biology": {"desc": "Protein folding, cryo-EM structures, macromolecular complexes, and conformational dynamics.", "aliases": ["cryo-EM", "protein structure", "crystallography", "folding"]},
        },
        "systems": {
            "model-organisms": {"desc": "Mice, Drosophila, C. elegans, zebrafish, yeast, Arabidopsis, and E. coli.", "aliases": ["mouse model", "drosophila", "c elegans", "zebrafish", "yeast", "arabidopsis"]},
            "microbial-communities": {"desc": "Gut microbiomes, environmental biofilms, viral populations, and soil consortia.", "aliases": ["microbiome", "biofilm", "viral population"]},
            "cellular-systems": {"desc": "Stem cells, primary cultures, organoids, and immortalized cell lines.", "aliases": ["stem cell", "organoid", "cell culture", "cell line"]},
            "organismal-populations": {"desc": "Wild animal populations, plant communities, and ecological cohorts.", "aliases": ["population", "cohort", "wild strain"]},
            "macromolecular-assemblies": {"desc": "Ribosomes, proteasomes, nuclear pore complexes, and membrane complexes.", "aliases": ["ribosome", "proteasome", "multiprotein complex"]},
        },
        "methods": {
            "next-generation-sequencing": {"desc": "RNA-seq, single-cell RNA-seq, ChIP-seq, whole-genome sequencing, and metagenomics.", "aliases": ["RNA-seq", "scRNA-seq", "ChIP-seq", "metagenomics", "WGS"]},
            "microscopy-imaging": {"desc": "Confocal fluorescence, super-resolution (STED/STORM), cryo-EM, and live-cell imaging.", "aliases": ["confocal", "super-resolution", "cryo-EM", "fluorescence microscopy"]},
            "gene-editing": {"desc": "CRISPR-Cas9, base editing, RNA interference (RNAi), and transgenesis.", "aliases": ["CRISPR", "Cas9", "base editing", "RNAi", "knockout"]},
            "biochemical-assays": {"desc": "Western blot, ELISA, enzymatic kinetics, pull-down assays, and mass spectrometry proteomics.", "aliases": ["western blot", "ELISA", "proteomics", "co-IP", "enzyme kinetics"]},
            "bioinformatic-pipelines": {"desc": "Differential expression analysis, genome assembly, phylogenetic trees, and structural modeling.", "aliases": ["differential expression", "tree building", "alignment pipeline", "clustering"]},
        }
    },
    {
        "id": "biomedical-clinical-sciences",
        "name": "Biomedical & Clinical Sciences",
        "category": "Medical & Clinical",
        "description": "Covers biological mechanisms of human disease and clinical research including neuroscience, immunology, oncology, pharmacology, pathology, metabolism and medical biotechnology.",
        "sampleTags": ["topic/neuroscience", "topic/immunology", "topic/cancer", "topic/pharmacology", "topic/pathology"],
        "topics": {
            "neuroscience": {"desc": "Neurodegeneration, synaptic plasticity, neural circuits, neuroinflammation, and brain disorders.", "aliases": ["alzheimer", "parkinson", "synaptic plasticity", "neurodegeneration", "neural circuit"]},
            "immunology": {"desc": "Innate/adaptive immunity, T-cell biology, auto-immunity, cytokines, and immunotherapy.", "aliases": ["T cell", "cytokine", "autoimmunity", "immunotherapy", "antibody", "innate immunity"]},
            "cancer": {"desc": "Oncogenesis, tumor microenvironment, metastasis, cancer genetics, and targeted oncology therapies.", "aliases": ["oncology", "tumor", "metastasis", "carcinoma", "chemotherapy", "car-t"]},
            "pharmacology": {"desc": "Pharmacodynamics, pharmacokinetics (ADME), drug delivery systems, and toxicology.", "aliases": ["pharmacokinetics", "ADME", "drug delivery", "toxicology", "pharmacodynamics"]},
            "pathology": {"desc": "Histopathology, molecular diagnostics, tissue pathogenesis, and biomarker identification.", "aliases": ["histopathology", "biomarker", "pathogenesis", "molecular diagnostic"]},
            "metabolism": {"desc": "Diabetes, lipid metabolism, mitochondrial dysfunction, metabolic syndrome, and bioenergetics.", "aliases": ["diabetes", "mitochondria", "lipid metabolism", "metabolic syndrome", "insulin"]},
            "infectious-disease": {"desc": "Viral/bacterial pathogenesis, antimicrobial resistance (AMR), vaccines, and host defense.", "aliases": ["AMR", "vaccine", "antimicrobial resistance", "viral infection", "pathogen"]},
            "medical-biotechnology": {"desc": "Gene therapy, monoclonal antibodies, regenerative medicine, and biosensing.", "aliases": ["gene therapy", "monoclonal antibody", "regenerative medicine", "cell therapy"]},
            "cardiovascular-medicine": {"desc": "Atherosclerosis, heart failure, vascular biology, arrhythmia, and thrombosis.", "aliases": ["cardiovascular", "atherosclerosis", "heart failure", "thrombosis", "vascular"]},
        },
        "systems": {
            "human-cohorts": {"desc": "Clinical trial participants, patient cohorts, healthy controls, and tissue biobanks.", "aliases": ["clinical cohort", "patient cohort", "biobank", "clinical trial"]},
            "animal-disease-models": {"desc": "Transgenic mice, xenografts (PDX), primate models, and disease-specific mutants.", "aliases": ["PDX", "transgenic mouse", "disease model", "xenograft"]},
            "cell-and-tissue-models": {"desc": "Patient-derived organoids, iPSCs, primary human cells, and organ-on-a-chip devices.", "aliases": ["organoid", "iPSC", "organ-on-a-chip", "primary culture"]},
            "biological-pathways": {"desc": "Signaling cascades, immune checkpoints, metabolic pathways, and gene networks.", "aliases": ["immune checkpoint", "signaling cascade", "metabolic pathway"]},
        },
        "methods": {
            "clinical-trials": {"desc": "Phase I-IV randomized controlled trials (RCT), blinding, and survival endpoints.", "aliases": ["RCT", "phase III", "randomized trial", "placebo-controlled"]},
            "flow-cytometry": {"desc": "FACS analysis, multi-color immunophenotyping, and CyTOF mass cytometry.", "aliases": ["FACS", "flow cytometry", "CyTOF", "immunophenotyping"]},
            "histopathology-imaging": {"desc": "Immunohistochemistry (IHC), spatial transcriptomics, and MRI/PET imaging.", "aliases": ["IHC", "spatial transcriptomics", "MRI", "PET scan", "histology"]},
            "pharmacokinetic-modeling": {"desc": "Compartmental PK/PD modeling, non-compartmental analysis, and dose-response curve fitting.", "aliases": ["PK/PD", "dose response", "clearance modeling"]},
            "biomarker-discovery": {"desc": "Liquid biopsy, targeted metabolomics, RNA sequencing, and diagnostic assay validation.", "aliases": ["liquid biopsy", "metabolomics", "biomarker validation"]},
        }
    },
    {
        "id": "health-sciences",
        "name": "Health Sciences",
        "category": "Public & Allied Health",
        "description": "Covers population and applied health research including epidemiology, public health, nursing, allied health, rehabilitation, health systems, exercise science and healthcare delivery.",
        "sampleTags": ["topic/epidemiology", "topic/public-health", "topic/health-services", "topic/nursing", "topic/health-policy"],
        "topics": {
            "epidemiology": {"desc": "Cohort studies, disease incidence, risk factors, infectious disease modeling, and causal inference.", "aliases": ["cohort study", "incidence", "prevalence", "risk factor", "case-control", "disease burden"]},
            "public-health": {"desc": "Health promotion, disease prevention, global health, health disparities, and environmental health.", "aliases": ["global health", "health promotion", "prevention", "health disparities", "social determinants"]},
            "health-services": {"desc": "Healthcare quality, clinical outcomes, patient safety, hospital operations, and telemedicine.", "aliases": ["healthcare delivery", "patient safety", "telemedicine", "quality of care", "clinical workflow"]},
            "nursing": {"desc": "Nursing care protocols, patient-centered care, nurse staffing, and clinical nursing practice.", "aliases": ["nursing care", "patient centered", "clinical nursing", "nursing education"]},
            "rehabilitation": {"desc": "Physical therapy, occupational therapy, functional recovery, and disability management.", "aliases": ["physical therapy", "occupational therapy", "physiotherapy", "disability"]},
            "allied-health": {"desc": "Dietetics, speech pathology, clinical psychology, podiatry, and diagnostic radiography.", "aliases": ["dietetics", "nutrition", "speech pathology", "radiography", "audiology"]},
            "exercise-science": {"desc": "Exercise physiology, biomechanics, sports performance, physical activity, and athletic training.", "aliases": ["biomechanics", "physical activity", "sports science", "exercise physiology", "kinesiology"]},
            "health-policy": {"desc": "Health economics, insurance systems, health technology assessment (HTA), and policy reform.", "aliases": ["health economics", "HTA", "insurance", "policy reform", "health expenditure"]},
        },
        "systems": {
            "health-systems": {"desc": "Hospitals, primary care clinics, national health services, and community care centers.", "aliases": ["hospital", "clinic", "health system", "NHS", "primary care"]},
            "target-populations": {"desc": "Elderly cohorts, pediatric patients, vulnerable communities, and workforce groups.", "aliases": ["elderly", "pediatric", "vulnerable population", "workers"]},
            "health-datasets": {"desc": "Electronic health records (EHR), national registry databases, and claims datasets.", "aliases": ["EHR", "health registry", "claims data", "vital statistics"]},
            "community-settings": {"desc": "Schools, workplaces, rural communities, and municipal health districts.", "aliases": ["community", "workplace", "rural health"]},
        },
        "methods": {
            "epidemiological-studies": {"desc": "Prospective cohort, case-control, cross-sectional, and ecological study designs.", "aliases": ["cohort study", "case-control", "cross-sectional", "incidence study"]},
            "health-economic-evaluation": {"desc": "Cost-effectiveness analysis (CEA), QALY calculations, and budget impact modeling.", "aliases": ["cost-effectiveness", "CEA", "QALY", "ICER", "budget impact"]},
            "implementation-science": {"desc": "Process evaluations, barrier analysis, fidelity metrics, and pragmatic trials.", "aliases": ["implementation science", "pragmatic trial", "process evaluation", "fidelity"]},
            "qualitative-health-research": {"desc": "In-depth patient interviews, focus groups, and phenomenological thematic analysis.", "aliases": ["patient interviews", "focus groups", "qualitative health"]},
            "biostatistical-modeling": {"desc": "Survival analysis (Cox models), logistic regression, and propensity score matching.", "aliases": ["survival analysis", "cox model", "propensity score", "logistic regression"]},
        }
    },
    {
        "id": "agricultural-veterinary-food",
        "name": "Agricultural, Veterinary & Food Sciences",
        "category": "Agricultural & Veterinary",
        "description": "Covers agriculture, agronomy, crop and animal production, forestry, fisheries, horticulture, food science and veterinary research.",
        "sampleTags": ["topic/agronomy", "topic/crop-science", "topic/animal-science", "topic/food-science", "topic/veterinary-science"],
        "topics": {
            "agronomy": {"desc": "Soil fertility, crop rotation, precision agriculture, irrigation management, and tillage systems.", "aliases": ["soil management", "precision agriculture", "irrigation", "tillage", "fertilizer"]},
            "crop-science": {"desc": "Plant breeding, crop genetics, yield optimization, drought resistance, and pest management.", "aliases": ["crop breeding", "plant genetics", "yield", "drought resistance", "pest resistance"]},
            "animal-science": {"desc": "Livestock genetics, animal nutrition, feed efficiency, reproduction, and welfare.", "aliases": ["livestock", "animal nutrition", "feed efficiency", "animal breeding", "welfare"]},
            "forestry": {"desc": "Silviculture, forest ecology, timber management, reforestation, and agroforestry.", "aliases": ["silviculture", "forest management", "timber", "agroforestry", "reforestation"]},
            "fisheries-aquaculture": {"desc": "Fish farming, marine harvesting, aquaculture nutrition, disease management, and stock assessment.", "aliases": ["aquaculture", "fish farming", "fisheries", "stock assessment", "mariculture"]},
            "horticulture": {"desc": "Fruit, vegetable, viticulture, floriculture, greenhouse cultivation, and postharvest quality.", "aliases": ["viticulture", "greenhouse", "postharvest", "orchard", "floriculture"]},
            "food-science": {"desc": "Food processing, food safety/microbiology, sensory analysis, food chemistry, and packaging.", "aliases": ["food technology", "food safety", "sensory analysis", "food chemistry", "fermentation"]},
            "veterinary-science": {"desc": "Veterinary clinical medicine, zoonoses, animal pathology, pharmacology, and veterinary surgery.", "aliases": ["veterinary medicine", "zoonosis", "animal disease", "veterinary clinical", "one health"]},
        },
        "systems": {
            "agricultural-crops": {"desc": "Cereal crops (wheat, rice, maize), legumes, oilseeds, fruits, and vegetables.", "aliases": ["wheat", "rice", "maize", "soybean", "crop plant"]},
            "livestock-animals": {"desc": "Cattle, sheep, swine, poultry, horses, and companion animals.", "aliases": ["cattle", "sheep", "poultry", "pig", "livestock herd"]},
            "aquatic-stocks": {"desc": "Salmon, shellfish, marine finfish, algae, and wild fisheries stocks.", "aliases": ["salmon", "shellfish", "fish stock"]},
            "food-matrices": {"desc": "Dairy products, processed meats, grains, beverages, and functional foods.", "aliases": ["dairy", "beverage", "processed food", "emulsion"]},
            "agricultural-ecosystems": {"desc": "Pastures, cropping soils, orchards, plantations, and farm watersheds.", "aliases": ["pasture", "cropland", "farm soil", "orchard"]},
        },
        "methods": {
            "field-trials": {"desc": "Randomized block designs, multi-location trials, and crop yield testing.", "aliases": ["field trial", "randomized block", "yield trial"]},
            "sensory-and-food-assays": {"desc": "Texture profiling, rheology, HPLC nutritional analysis, and microbial plating.", "aliases": ["rheology", "sensory panel", "food testing", "HPLC analysis"]},
            "genomic-selection": {"desc": "Genome-wide association studies (GWAS), marker-assisted selection, and QTL mapping.", "aliases": ["genomic selection", "GWAS", "QTL", "marker-assisted"]},
            "veterinary-diagnostics": {"desc": "Necropsy, serological assays, PCR pathogen detection, and clinical examinations.", "aliases": ["necropsy", "serology", "PCR diagnostic", "clinical vet exam"]},
            "remote-sensing-agriculture": {"desc": "Drone multispectral imaging, NDVI vegetation index, and soil moisture probes.", "aliases": ["NDVI", "drone imaging", "multispectral", "precision sensing"]},
        }
    },
    {
        "id": "earth-atmospheric-ocean",
        "name": "Earth, Atmospheric & Ocean Sciences",
        "category": "Earth & Environmental",
        "description": "Covers geology, geophysics, geochemistry, atmospheric science, hydrology, oceanography, physical geography and planetary-scale Earth processes.",
        "sampleTags": ["topic/geology", "topic/geophysics", "topic/atmospheric-science", "topic/oceanography", "topic/climate-science"],
        "topics": {
            "geology": {"desc": "Sedimentology, structural geology, plate tectonics, stratigraphy, and petrology.", "aliases": ["tectonics", "sedimentology", "petrology", "stratigraphy", "volcanology"]},
            "geophysics": {"desc": "Seismology, geomagnetism, gravity surveying, geodynamics, and exploration geophysics.", "aliases": ["seismology", "geomagnetism", "geodynamics", "seismic survey"]},
            "geochemistry": {"desc": "Isotope geochemistry, mineral-water reactions, biogeochemistry, and geochronology.", "aliases": ["isotope", "geochronology", "radiometric dating", "mineral reaction"]},
            "atmospheric-science": {"desc": "Atmospheric dynamics, cloud microphysics, meteorology, aerosol chemistry, and weather forecasting.", "aliases": ["meteorology", "aerosol", "atmospheric chemistry", "weather forecast", "boundary layer"]},
            "hydrology": {"desc": "Surface water flow, groundwater aquifers, catchment modeling, watershed dynamics, and flood risk.", "aliases": ["groundwater", "aquifer", "catchment", "watershed", "river runoff", "flood modeling"]},
            "oceanography": {"desc": "Physical oceanography, thermohaline circulation, marine biogeochemistry, tides, and waves.", "aliases": ["ocean circulation", "marine chemistry", "thermohaline", "ocean current", "sea surface temperature"]},
            "climate-science": {"desc": "Global climate modeling, paleoclimate reconstructions, greenhouse warming, and climate tipping points.", "aliases": ["climate modeling", "paleoclimate", "global warming", "IPCC", "climate feedback"]},
            "geoscience": {"desc": "Mineral exploration, geomorphology, remote sensing, and planetary geology.", "aliases": ["mineral exploration", "geomorphology", "remote sensing", "planetary geology"]},
        },
        "systems": {
            "planetary-spheres": {"desc": "Atmosphere, lithosphere, hydrosphere, cryosphere, and oceanic water column.", "aliases": ["atmosphere", "ocean", "lithosphere", "ice sheet", "glacier"]},
            "geological-formations": {"desc": "Sedimentary basins, volcanic arcs, fault zones, and mineral deposits.", "aliases": ["fault zone", "sedimentary basin", "volcano", "ore deposit"]},
            "catchments-and-aquifers": {"desc": "River catchments, groundwater aquifers, estuaries, and deltaic systems.", "aliases": ["river basin", "aquifer", "estuary", "watershed"]},
            "oceanic-basins": {"desc": "Deep sea trenches, continental shelves, gyres, and coral reef ecosystems.", "aliases": ["continental shelf", "ocean gyre", "deep sea"]},
        },
        "methods": {
            "climate-and-earth-modeling": {"desc": "Coupled general circulation models (GCMs), WRF numerical weather models, and hydro-models.", "aliases": ["GCM", "WRF", "earth system model", "numerical weather model"]},
            "isotope-and-mass-spectrometry": {"desc": "Stable isotope ratios, radiocarbon dating, ICP-MS, and laser ablation analysis.", "aliases": ["ICP-MS", "stable isotope", "radiocarbon", "argon dating"]},
            "seismic-and-geophysical-survey": {"desc": "Seismic reflection/refraction, magnetotellurics, and gravimetry.", "aliases": ["seismic reflection", "magnetotellurics", "gravity survey"]},
            "satellite-remote-sensing": {"desc": "Synthetic aperture radar (SAR), satellite altimetry, lidar, and multispectral Earth observation.", "aliases": ["InSAR", "altimetry", "satellite observation", "lidar"]},
            "field-sampling-drilling": {"desc": "Ice cores, ocean sediment cores, borehole drilling, and hydrological field logging.", "aliases": ["ice core", "sediment core", "borehole", "water sampling"]},
        }
    },
    {
        "id": "environmental-sustainability",
        "name": "Environmental & Sustainability Sciences",
        "category": "Earth & Environmental",
        "description": "Covers ecosystems, biodiversity, pollution, conservation, environmental management, climate impacts, soils and sustainability.",
        "sampleTags": ["topic/ecology", "topic/conservation", "topic/biodiversity", "topic/sustainability", "topic/environmental-management"],
        "topics": {
            "ecology": {"desc": "Community ecology, food webs, trophic interactions, ecosystem metabolism, and landscape ecology.", "aliases": ["community ecology", "food web", "trophic", "ecosystem ecology", "landscape ecology"]},
            "conservation": {"desc": "Protected area management, endangered species recovery, habitat restoration, and rewilding.", "aliases": ["habitat restoration", "protected area", "species recovery", "rewilding", "conservation biology"]},
            "biodiversity": {"desc": "Species richness, phylogenetic diversity, functional traits, and extinction risk analysis.", "aliases": ["species richness", "extinction risk", "functional diversity", "IUCN"]},
            "pollution": {"desc": "Air quality, water contamination, microplastics, ecotoxicology, and heavy metal remediation.", "aliases": ["ecotoxicology", "microplastics", "contaminants", "remediation", "heavy metals", "water pollution"]},
            "environmental-management": {"desc": "Environmental impact assessment (EIA), natural resource governance, and adaptive management.", "aliases": ["EIA", "resource governance", "adaptive management", "environmental policy"]},
            "climate-adaptation": {"desc": "Vulnerability assessment, climate resilience, nature-based solutions, and disaster mitigation.", "aliases": ["climate resilience", "nature-based solutions", "adaptation", "vulnerability"]},
            "soil-science": {"desc": "Soil carbon sequestration, soil microbiome, erosion control, and pedology.", "aliases": ["soil carbon", "soil microbiome", "pedology", "soil erosion", "soil health"]},
            "sustainability": {"desc": "Circular economy, life cycle assessment (LCA), sustainable development goals (SDGs), and resource efficiency.", "aliases": ["circular economy", "LCA", "life cycle assessment", "SDGs", "sustainability metrics"]},
        },
        "systems": {
            "terrestrial-ecosystems": {"desc": "Tropical forests, temperate woodlands, grasslands, savannas, and arid ecosystems.", "aliases": ["forest", "grassland", "savanna", "wetland"]},
            "aquatic-ecosystems": {"desc": "Rivers, freshwater lakes, coastal wetlands, mangroves, and coral reefs.", "aliases": ["mangrove", "coral reef", "freshwater lake", "river ecosystem"]},
            "anthropogenic-environments": {"desc": "Agricultural landscapes, urban green spaces, mining sites, and industrial zones.", "aliases": ["urban ecosystem", "mine site", "agricultural landscape"]},
            "social-ecological-systems": {"desc": "Coupled human-environment systems, governance regimes, and resource common pools.", "aliases": ["social-ecological system", "common pool resource"]},
        },
        "methods": {
            "ecological-field-survey": {"desc": "Transect sampling, camera traps, environmental DNA (eDNA), and acoustic monitoring.", "aliases": ["eDNA", "camera trap", "transect", "acoustic monitoring", "quadrat"]},
            "life-cycle-assessment": {"desc": "ISO-standard LCA modeling, carbon footprinting, and cradle-to-grave analysis.", "aliases": ["LCA", "carbon footprint", "cradle-to-grave", "material flow"]},
            "ecotoxicological-bioassays": {"desc": "Toxicity testing, bioaccumulation assays, and chemical pollutant screening.", "aliases": ["bioassay", "toxicity test", "bioaccumulation", "LC50"]},
            "spatial-gis-modeling": {"desc": "Species distribution modeling (MaxEnt), GIS mapping, and habitat fragmentation metrics.", "aliases": ["MaxEnt", "species distribution model", "GIS", "spatial analysis"]},
            "ecosystem-carbon-accounting": {"desc": "Eddy covariance towers, soil core carbon analysis, and biomass allometry.", "aliases": ["eddy covariance", "carbon stock", "biomass estimation"]},
        }
    },
    {
        "id": "engineering-technology",
        "name": "Engineering & Technology",
        "category": "Engineering & Tech",
        "description": "Covers electrical, mechanical, chemical, civil, aerospace, biomedical, environmental, manufacturing, materials and control engineering.",
        "sampleTags": ["topic/electrical-engineering", "topic/mechanical-engineering", "topic/chemical-engineering", "topic/robotics", "topic/materials-engineering"],
        "topics": {
            "electrical-engineering": {"desc": "Power systems, renewable grid integration, microelectronics, RF engineering, and signal processing.", "aliases": ["power grid", "microelectronics", "signal processing", "RF", "semiconductor devices", "VLSI"]},
            "mechanical-engineering": {"desc": "Solid mechanics, thermodynamics, fluid dynamics, heat transfer, and tribology.", "aliases": ["fluid mechanics", "heat transfer", "thermodynamics", "tribology", "finite element analysis"]},
            "chemical-engineering": {"desc": "Process intensification, separation processes, reaction engineering, fluidization, and scaling.", "aliases": ["reactor design", "process control", "separation process", "mass transfer", "distillation"]},
            "civil-engineering": {"desc": "Structural engineering, concrete/steel design, geotechnical mechanics, and transportation engineering.", "aliases": ["structural engineering", "geotechnical", "concrete", "transportation infrastructure", "seismic design"]},
            "aerospace-engineering": {"desc": "Aerodynamics, propulsion systems, flight dynamics, satellite mechanics, and composite structures.", "aliases": ["aerodynamics", "propulsion", "flight control", "avionics", "spacecraft"]},
            "robotics": {"desc": "Kinematics, autonomous navigation, robotic manipulation, control theory, and soft robotics.", "aliases": ["control systems", "autonomous robot", "manipulation", "SLAM", "soft robotics", "actuators"]},
            "materials-engineering": {"desc": "Alloy design, ceramics, composite fabrication, failure analysis, and additive manufacturing.", "aliases": ["alloys", "composites", "failure analysis", "additive manufacturing", "metallurgy"]},
            "manufacturing": {"desc": "Industry 4.0, computer-aided design (CAD/CAM), machining, quality control, and supply chain manufacturing.", "aliases": ["CAD/CAM", "machining", "industry 4.0", "lean manufacturing", "process optimization"]},
        },
        "systems": {
            "mechanical-structures": {"desc": "Turbines, engines, airframes, bridges, pressure vessels, and robotic mechanisms.", "aliases": ["turbine", "engine", "bridge", "airframe", "robot arm"]},
            "power-and-energy-systems": {"desc": "Inverters, smart grids, battery packs, wind farms, and photovoltaic arrays.", "aliases": ["smart grid", "inverter", "battery pack", "wind turbine"]},
            "chemical-reactors": {"desc": "Packed bed reactors, distillation columns, membrane modules, and microreactors.", "aliases": ["reactor", "distillation column", "membrane unit"]},
            "electronic-circuits": {"desc": "Integrated circuits (ICs), PCB boards, sensor nodes, and power converters.", "aliases": ["IC", "PCB", "converter", "microcontroller"]},
            "engineered-materials": {"desc": "High-entropy alloys, carbon fiber composites, functional ceramics, and metamaterials.", "aliases": ["alloy", "carbon fiber", "composite material"]},
        },
        "methods": {
            "finite-element-analysis": {"desc": "Structural stress analysis (FEA), modal analysis, and dynamic crash simulation.", "aliases": ["FEA", "finite element", "stress analysis", "ansys"]},
            "computational-fluid-dynamics": {"desc": "Navier-Stokes solvers, turbulence modeling (LES/RANS), and aerodynamic simulation.", "aliases": ["CFD", "LES", "RANS", "fluent", "openfoam"]},
            "experimental-prototyping": {"desc": "3D printing, wind tunnel testing, tensile load testing, and benchtop prototyping.", "aliases": ["wind tunnel", "tensile test", "rapid prototyping", "3D printing"]},
            "control-system-design": {"desc": "PID control, model predictive control (MPC), state-space feedback, and Kalman filtering.", "aliases": ["MPC", "PID", "kalman filter", "state space control"]},
            "characterisation-testing": {"desc": "Scanning electron microscopy (SEM), fatigue testing, non-destructive testing (NDT), and vibration test.", "aliases": ["SEM", "fatigue test", "NDT", "vibration analysis"]},
        }
    },
    {
        "id": "built-environment-architecture",
        "name": "Built Environment, Architecture & Planning",
        "category": "Built Environment",
        "description": "Covers architecture, building science, urban and regional planning, infrastructure design and the interaction between people and constructed environments.",
        "sampleTags": ["topic/architecture", "topic/urban-planning", "topic/building-science", "topic/sustainable-design", "topic/housing"],
        "topics": {
            "architecture": {"desc": "Architectural theory, spatial design, historical preservation, architectural morphology, and parametric design.", "aliases": ["spatial design", "architectural theory", "parametric design", "heritage preservation"]},
            "urban-planning": {"desc": "Zoning, land-use planning, smart cities, transit-oriented development, and regional growth.", "aliases": ["land use", "zoning", "smart cities", "transit-oriented development", "urban growth"]},
            "building-science": {"desc": "Thermal comfort, building envelope, indoor air quality (IAQ), acoustics, and daylighting.", "aliases": ["indoor air quality", "thermal comfort", "building envelope", "acoustics", "daylighting"]},
            "urban-design": {"desc": "Public space design, pedestrian walkability, streetscapes, and placemaking.", "aliases": ["public space", "walkability", "streetscape", "placemaking", "urban form"]},
            "housing": {"desc": "Housing affordability, residential density, social housing, tenancy, and informal settlements.", "aliases": ["affordable housing", "social housing", "tenancy", "housing density"]},
            "infrastructure": {"desc": "Urban transport networks, water/energy utilities, civic facilities, and resilient infrastructure.", "aliases": ["transport network", "civic infrastructure", "utility networks", "resilient infrastructure"]},
            "sustainable-design": {"desc": "Net-zero buildings, circular construction materials, green infrastructure, and LEED/BREEAM.", "aliases": ["net-zero building", "green infrastructure", "circular construction", "LEED", "passive design"]},
        },
        "systems": {
            "buildings-and-envelopes": {"desc": "Residential towers, commercial complexes, educational facilities, and historic facades.", "aliases": ["building", "residential tower", "commercial building", "facade"]},
            "urban-neighbourhoods": {"desc": "City precincts, public plazas, transit hubs, and residential suburbs.", "aliases": ["neighborhood", "precinct", "public square", "suburb"]},
            "infrastructure-networks": {"desc": "Rail networks, highway corridors, stormwater systems, and district heating.", "aliases": ["rail corridor", "stormwater network", "road network"]},
            "construction-materials": {"desc": "Mass timber, low-carbon concrete, insulation materials, and glazing systems.", "aliases": ["mass timber", "green concrete", "glazing", "insulation"]},
        },
        "methods": {
            "building-energy-simulation": {"desc": "EnergyPlus modeling, thermal load calculation, and computational daylight analysis.", "aliases": ["EnergyPlus", "thermal simulation", "daylight modeling", "building simulation"]},
            "spatial-and-gis-analysis": {"desc": "Space syntax, GIS multi-criteria evaluation, and demographic spatial modeling.", "aliases": ["space syntax", "GIS mapping", "spatial multicriteria"]},
            "post-occupancy-evaluation": {"desc": "Occupant surveys, indoor sensor logging, and thermal comfort benchmarking.", "aliases": ["POE", "occupant survey", "sensor logging", "comfort monitoring"]},
            "parametric-cad-modeling": {"desc": "BIM modeling, generative Grasshopper design, and digital twin simulation.", "aliases": ["BIM", "digital twin", "grasshopper", "revit"]},
            "urban-fieldwork-interviews": {"desc": "Participatory design workshops, stakeholder interviews, and site observation.", "aliases": ["participatory planning", "site observation", "stakeholder workshop"]},
        }
    },
    {
        "id": "psychology-cognitive-sciences",
        "name": "Psychology & Cognitive Sciences",
        "category": "Behavioral Sciences",
        "description": "Covers cognitive, behavioural, developmental, biological, social, personality, clinical and computational psychology.",
        "sampleTags": ["topic/cognition", "topic/behaviour", "topic/cognitive-neuroscience", "topic/mental-health", "topic/decision-making"],
        "topics": {
            "cognition": {"desc": "Working memory, attention, executive function, language comprehension, and mental representation.", "aliases": ["working memory", "attention", "executive function", "cognitive control", "memory"]},
            "behaviour": {"desc": "Operant/classical conditioning, habit formation, motivation, motor control, and behavioral change.", "aliases": ["conditioning", "habit", "motivation", "behavior change", "motor control"]},
            "developmental-psychology": {"desc": "Child development, cognitive aging, lifespan development, attachment, and language acquisition.", "aliases": ["child development", "aging", "attachment theory", "lifespan", "language acquisition"]},
            "social-psychology": {"desc": "Social cognition, intergroup relations, prejudice, conformity, empathy, and moral judgment.", "aliases": ["social cognition", "intergroup bias", "conformity", "empathy", "moral psychology"]},
            "cognitive-neuroscience": {"desc": "Neural correlates of cognition, fMRI/EEG neural dynamics, and brain connectivity.", "aliases": ["fMRI", "EEG", "neural correlates", "brain connectivity", "neuroimaging"]},
            "decision-making": {"desc": "Heuristics and biases, prospect theory, risk preferences, and neuroeconomics.", "aliases": ["heuristics", "biases", "prospect theory", "risk preference", "choice architecture"]},
            "perception": {"desc": "Visual perception, auditory processing, multisensory integration, and psychophysics.", "aliases": ["visual perception", "auditory", "psychophysics", "multisensory"]},
            "mental-health": {"desc": "Psychopathology, depression, anxiety, trauma/PTSD, psychotherapy outcomes, and resilience.", "aliases": ["depression", "anxiety", "PTSD", "psychopathology", "psychotherapy", "resilience"]},
        },
        "systems": {
            "human-participants": {"desc": "Undergraduate cohorts, clinical psychiatric cohorts, children, and aging adults.", "aliases": ["participants", "clinical cohort", "student sample", "healthy volunteers"]},
            "cognitive-architectures": {"desc": "Connectionist models, ACT-R architectures, and drift-diffusion decision models.", "aliases": ["drift diffusion", "ACT-R", "connectionist model"]},
            "neural-circuits": {"desc": "Prefrontal cortex, amygdala, hippocampus, and default mode network (DMN).", "aliases": ["prefrontal cortex", "hippocampus", "DMN", "amygdala"]},
            "social-groups": {"desc": "Small decision groups, peer networks, romantic dyads, and cultural groups.", "aliases": ["dyad", "peer group", "decision team"]},
        },
        "methods": {
            "behavioral-experiments": {"desc": "Reaction-time tasks, eye-tracking experiments, and computerized cognitive paradigms.", "aliases": ["reaction time", "eye tracking", "stroop task", "cognitive test"]},
            "neuroimaging-eeg": {"desc": "Task-based fMRI, event-related potentials (ERP), EEG band power, and MEG.", "aliases": ["fMRI", "EEG", "ERP", "MEG", "neuroimaging"]},
            "psychometric-measurement": {"desc": "Validated questionnaires, factor analysis (CFA/EFA), and item response theory (IRT).", "aliases": ["factor analysis", "IRT", "psychometrics", "questionnaire scale"]},
            "computational-cognitive-modeling": {"desc": "Bayesian cognitive modeling, reinforcement learning models, and neural network simulations.", "aliases": ["bayesian cognitive model", "reinforcement learning model", "computational model"]},
            "clinical-intervention-trials": {"desc": "Randomized psychotherapy trials (CBT/mindfulness) and clinical symptom scoring.", "aliases": ["CBT trial", "psychotherapy outcome", "clinical scoring"]},
        }
    },
    {
        "id": "economics",
        "name": "Economics",
        "category": "Economic Sciences",
        "description": "Covers economic theory, applied economics, econometrics, macroeconomics, microeconomics, labour, development, public and behavioural economics.",
        "sampleTags": ["topic/econometrics", "topic/macroeconomics", "topic/microeconomics", "topic/labour-economics", "topic/behavioural-economics"],
        "topics": {
            "econometrics": {"desc": "Identification strategies, panel data methods, instrumental variables (IV), and time-series econometrics.", "aliases": ["instrumental variables", "difference-in-differences", "panel data", "time series", "causal identification"]},
            "macroeconomics": {"desc": "Monetary policy, fiscal policy, business cycles, inflation, economic growth, and DSGE modeling.", "aliases": ["monetary policy", "fiscal policy", "inflation", "business cycle", "DSGE", "growth theory"]},
            "microeconomics": {"desc": "Game theory, mechanism design, consumer choice, market equilibrium, and industrial organisation.", "aliases": ["game theory", "mechanism design", "industrial organization", "market structure", "pricing"]},
            "labour-economics": {"desc": "Wage inequality, employment, human capital, labor market friction, and migration economics.", "aliases": ["wage inequality", "employment", "human capital", "minimum wage", "labor market"]},
            "development-economics": {"desc": "Poverty traps, microcredit, foreign aid, institutional economics, and randomized evaluations.", "aliases": ["poverty", "microfinance", "RCT development", "institutions", "economic development"]},
            "public-economics": {"desc": "Taxation theory, public goods, social insurance, redistribution, and fiscal federalism.", "aliases": ["taxation", "public goods", "social insurance", "redistribution", "welfare economics"]},
            "behavioural-economics": {"desc": "Time inconsistency, social preferences, bounded rationality, nudges, and behavioral games.", "aliases": ["nudge", "time inconsistency", "loss aversion", "behavioral finance", "social preferences"]},
        },
        "systems": {
            "national-economies": {"desc": "OECD economies, emerging markets, central banking systems, and currency areas.", "aliases": ["national economy", "central bank", "emerging market", "eurozone"]},
            "markets-and-firms": {"desc": "Oligopolies, competitive markets, labor markets, and auction platforms.", "aliases": ["firm", "market", "auction", "industry"]},
            "households-and-workers": {"desc": "Representative consumers, worker cohorts, household panels, and low-income families.", "aliases": ["household", "worker", "consumer cohort"]},
            "economic-datasets": {"desc": "Census data, administrative tax records, central bank time-series, and household surveys.", "aliases": ["census data", "tax records", "household survey", "panel study"]},
        },
        "methods": {
            "quasi-experimental-econometrics": {"desc": "Difference-in-differences (DiD), regression discontinuity (RD), and synthetic controls.", "aliases": ["DiD", "regression discontinuity", "synthetic control", "event study"]},
            "structural-estimation": {"desc": "Dynamic discrete choice, generalized method of moments (GMM), and maximum simulated likelihood.", "aliases": ["structural model", "GMM", "dynamic discrete choice"]},
            "macroeconomic-dsge-simulation": {"desc": "Dynamic stochastic general equilibrium (DSGE) solving, calibration, and Bayesian estimation.", "aliases": ["DSGE", "calibration", "VAR", "vector autoregression"]},
            "randomized-control-trials": {"desc": "Field experiments, intervention trials, and A/B policy evaluations.", "aliases": ["field experiment", "RCT economics", "policy evaluation"]},
            "game-theoretic-proof": {"desc": "Nash equilibrium analysis, subgame perfection, and auction mechanism proofs.", "aliases": ["nash equilibrium", "mechanism proof", "subgame perfect"]},
        }
    },
    {
        "id": "business-management-organisations",
        "name": "Business, Management & Organisations",
        "category": "Business & Management",
        "description": "Covers finance, accounting, management, marketing, organisational behaviour, strategy, entrepreneurship, logistics, tourism and operations.",
        "sampleTags": ["topic/finance", "topic/management", "topic/marketing", "topic/strategy", "topic/entrepreneurship"],
        "topics": {
            "finance": {"desc": "Asset pricing, corporate finance, market microstructure, portfolio management, and financial risk.", "aliases": ["asset pricing", "corporate finance", "portfolio management", "risk management", "fintech"]},
            "accounting": {"desc": "Financial reporting, auditing, managerial accounting, earnings management, and corporate governance.", "aliases": ["auditing", "financial reporting", "earnings management", "managerial accounting"]},
            "management": {"desc": "Leadership, strategic human resources, organisational change, and business ethics.", "aliases": ["leadership", "human resource management", "HRM", "organizational change", "governance"]},
            "marketing": {"desc": "Consumer behavior, brand management, digital marketing, pricing strategy, and customer analytics.", "aliases": ["consumer behavior", "branding", "digital marketing", "customer analytics", "advertising"]},
            "organisational-behaviour": {"desc": "Team dynamics, workplace motivation, employee turnover, organisational culture, and conflict.", "aliases": ["organizational culture", "employee engagement", "team dynamics", "workplace motivation"]},
            "strategy": {"desc": "Competitive advantage, resource-based view (RBV), mergers & acquisitions (M&A), and platform ecosystems.", "aliases": ["competitive strategy", "RBV", "M&A", "business model", "platform strategy"]},
            "entrepreneurship": {"desc": "Venture capital, startup ecosystems, innovation management, and corporate entrepreneurship.", "aliases": ["venture capital", "startup", "innovation management", "business incubation"]},
            "supply-chain": {"desc": "Logistics optimization, procurement, inventory theory, supply chain resilience, and operations.", "aliases": ["operations management", "logistics", "inventory", "procurement", "supply chain resilience"]},
        },
        "systems": {
            "corporations-and-enterprises": {"desc": "Publicly traded firms, multinational corporations (MNCs), and SMEs.", "aliases": ["corporation", "firm", "MNC", "SME", "enterprise"]},
            "financial-markets": {"desc": "Stock exchanges, bond markets, derivatives markets, and cryptocurrency networks.", "aliases": ["stock market", "bond market", "derivatives", "crypto"]},
            "supply-networks": {"desc": "Global freight corridors, multi-tier supplier networks, and distribution hubs.", "aliases": ["supplier network", "freight corridor", "distribution hub"]},
            "organisational-workforces": {"desc": "Executive boards, management teams, knowledge workers, and frontline staff.", "aliases": ["workforce", "board of directors", "management team"]},
        },
        "methods": {
            "financial-econometrics": {"desc": "Fama-MacBeth regressions, event studies, panel regressions, and GARCH volatility models.", "aliases": ["event study", "fama macbeth", "GARCH", "portfolio sort"]},
            "structural-equation-modeling": {"desc": "PLS-SEM, covariance-based SEM, factor analysis, and mediation/moderation analysis.", "aliases": ["SEM", "PLS-SEM", "mediation analysis", "survey analysis"]},
            "case-study-research": {"desc": "Qualitative multiple-case studies, process tracing, and inductive theory building.", "aliases": ["case study", "multiple case", "inductive research", "grounded theory"]},
            "operations-optimization": {"desc": "Linear/integer programming, queueing models, discrete-event simulation, and heuristics.", "aliases": ["discrete event simulation", "queueing theory", "integer programming"]},
            "experimental-consumer-studies": {"desc": "Laboratory consumer experiments, conjoint analysis, and online A/B testing.", "aliases": ["conjoint analysis", "consumer experiment", "A/B test"]},
        }
    },
    {
        "id": "society-politics-human-geography",
        "name": "Society, Politics & Human Geography",
        "category": "Social Sciences",
        "description": "Covers sociology, anthropology, demography, political science, public policy, development studies, human geography, social work and related studies of human societies.",
        "sampleTags": ["topic/sociology", "topic/political-science", "topic/public-policy", "topic/anthropology", "topic/human-geography"],
        "topics": {
            "sociology": {"desc": "Social stratification, inequality, gender studies, race/ethnicity, and social movements.", "aliases": ["social inequality", "stratification", "gender studies", "social movements", "sociological theory"]},
            "anthropology": {"desc": "Cultural anthropology, ethnography, kinship, ritual practices, and material culture.", "aliases": ["ethnography", "cultural anthropology", "kinship", "ritual", "fieldwork"]},
            "political-science": {"desc": "Comparative politics, democratic institutions, authoritarianism, electoral systems, and political theory.", "aliases": ["comparative politics", "elections", "democracy", "authoritarianism", "political theory"]},
            "public-policy": {"desc": "Policy evaluation, agenda setting, regulatory governance, policy diffusion, and public administration.", "aliases": ["policy analysis", "public administration", "governance", "policy diffusion"]},
            "demography": {"desc": "Fertility, mortality, population aging, migration flows, and demographic transitions.", "aliases": ["migration", "fertility", "population aging", "mortality", "demographic transition"]},
            "development-studies": {"desc": "Global south development, agrarian change, community empowerment, and structural adjustment.", "aliases": ["international development", "global south", "agrarian change", "aid"]},
            "human-geography": {"desc": "Spatial inequality, urban geography, political geography, gentrification, and mobilities.", "aliases": ["urban geography", "gentrification", "spatial politics", "mobilities", "geopolitics"]},
            "social-work": {"desc": "Child welfare, community development, social justice practice, and human services delivery.", "aliases": ["child welfare", "social care", "community work", "human services"]},
        },
        "systems": {
            "nation-states-and-polities": {"desc": "Governments, legislatures, political parties, and state apparatuses.", "aliases": ["nation state", "government", "parliament", "political party"]},
            "social-groups-and-classes": {"desc": "Working class communities, migrant diasporas, marginalized groups, and elite networks.", "aliases": ["diaspora", "working class", "minority group", "elite network"]},
            "urban-and-regional-spaces": {"desc": "Metropolitan regions, rural municipalities, border zones, and informal settlements.", "aliases": ["megacity", "rural community", "borderland", "informal settlement"]},
            "international-institutions": {"desc": "United Nations agencies, international NGOs, regional pacts, and global treaties.", "aliases": ["UN", "NGO", "international treaty", "transnational body"]},
        },
        "methods": {
            "ethnographic-fieldwork": {"desc": "Participant observation, deep immersion, field notes, and reflexive ethnography.", "aliases": ["participant observation", "ethnography", "fieldwork"]},
            "comparative-political-analysis": {"desc": "Qualitative comparative analysis (QCA), cross-national regression, and case comparisons.", "aliases": ["QCA", "cross-national comparison", "comparative politics method"]},
            "survey-and-demographic-analysis": {"desc": "National social surveys, demographic life tables, census microdata analysis, and weights.", "aliases": ["social survey", "life table", "demographic analysis"]},
            "discourse-and-textual-analysis": {"desc": "Critical discourse analysis (CDA), policy document coding, and political rhetoric analysis.", "aliases": ["CDA", "discourse analysis", "document coding", "content analysis"]},
            "spatial-social-gis": {"desc": "Geodemographic profiling, spatial autocorrelation (Moran's I), and spatial regression.", "aliases": ["spatial regression", "geodemographics", "spatial analysis social"]},
        }
    },
    {
        "id": "education-learning-sciences",
        "name": "Education & Learning Sciences",
        "category": "Education",
        "description": "Covers teaching, learning, curriculum, pedagogy, educational psychology, educational technology, assessment, education systems and policy.",
        "sampleTags": ["topic/pedagogy", "topic/curriculum", "topic/learning", "topic/educational-technology", "topic/higher-education"],
        "topics": {
            "pedagogy": {"desc": "Teaching strategies, instructional design, active learning, inclusive education, and classroom practices.", "aliases": ["instructional design", "active learning", "teaching methods", "inclusive teaching"]},
            "curriculum": {"desc": "Curriculum theory, STEM education, literacy/numeracy, standards, and syllabus reform.", "aliases": ["STEM education", "literacy", "numeracy", "curriculum reform", "syllabus"]},
            "learning": {"desc": "Cognitive load theory, conceptual change, self-regulated learning, and knowledge acquisition.", "aliases": ["cognitive load", "self-regulated learning", "conceptual change", "learning process"]},
            "assessment": {"desc": "Formative/summative assessment, standardized testing, rubric design, and psychometric validation.", "aliases": ["formative assessment", "summative assessment", "standardized testing", "rubrics"]},
            "educational-technology": {"desc": "Learning analytics, online/blended learning, intelligent tutoring, AI in education, and MOOCs.", "aliases": ["edtech", "learning analytics", "online learning", "AI in education", "intelligent tutoring"]},
            "higher-education": {"desc": "University teaching, graduate employability, academic retention, and student experience.", "aliases": ["university education", "student retention", "tertiary education", "employability"]},
            "education-policy": {"desc": "School governance, education funding, teacher workforce policy, and educational equity.", "aliases": ["school governance", "teacher policy", "education equity", "funding reform"]},
            "early-childhood-and-schooling": {"desc": "Early childhood education (ECEC), primary/secondary schooling, and special education.", "aliases": ["early childhood", "primary school", "secondary school", "special education"]},
        },
        "systems": {
            "educational-institutions": {"desc": "Primary/secondary schools, vocational colleges, universities, and preschools.", "aliases": ["school", "university", "college", "preschool", "classroom"]},
            "student-cohorts": {"desc": "Undergraduate students, K-12 pupils, neurodiverse learners, and adult trainees.", "aliases": ["students", "pupils", "learners", "trainees"]},
            "learning-platforms": {"desc": "Learning management systems (LMS/Canvas/Moodle), adaptive tutors, and digital classrooms.", "aliases": ["LMS", "canvas", "moodle", "digital classroom"]},
            "education-systems": {"desc": "State education departments, national testing authorities, and school districts.", "aliases": ["education ministry", "school district", "exam authority"]},
        },
        "methods": {
            "classroom-action-research": {"desc": "Teacher-researcher cycles, participatory action research, and classroom interventions.", "aliases": ["action research", "classroom observation", "lesson study"]},
            "quasi-experimental-education-trials": {"desc": "Clustered randomized trials in schools, difference-in-differences, and value-added modeling.", "aliases": ["cluster RCT", "school trial", "value-added model"]},
            "learning-analytics-data-mining": {"desc": "Clickstream analysis, log-file mining, discourse analytics, and predictive student modeling.", "aliases": ["clickstream", "log analysis", "educational data mining"]},
            "qualitative-educational-studies": {"desc": "Student/teacher interviews, classroom video coding, and educational case studies.", "aliases": ["teacher interview", "classroom coding", "video analysis"]},
            "psychometric-educational-testing": {"desc": "Item response theory (IRT), Rasch modeling, and test score reliability analysis.", "aliases": ["IRT education", "rasch model", "test reliability"]},
        }
    },
    {
        "id": "law-criminology-justice",
        "name": "Law, Criminology & Justice",
        "category": "Law & Justice",
        "description": "Covers legal systems, public and private law, international law, commercial and environmental law, criminology, justice and regulation.",
        "sampleTags": ["topic/public-law", "topic/private-law", "topic/international-law", "topic/criminology", "topic/criminal-justice"],
        "topics": {
            "public-law": {"desc": "Constitutional law, administrative law, judicial review, statutory interpretation, and human rights.", "aliases": ["constitutional law", "administrative law", "judicial review", "human rights law"]},
            "private-law": {"desc": "Contract law, tort law, property law, equity, trusts, and obligations.", "aliases": ["contract law", "tort law", "property law", "equity and trusts", "remedies"]},
            "international-law": {"desc": "Public international law, treaties, laws of armed conflict, international humanitarian law, and sovereignty.", "aliases": ["treaty law", "international humanitarian law", "UNCLOS", "sovereignty"]},
            "commercial-law": {"desc": "Corporate governance law, intellectual property (IP), competition/antitrust, and trade law.", "aliases": ["corporate law", "intellectual property", "antitrust", "trade law", "patent law"]},
            "environmental-law": {"desc": "Climate litigation, planning law, biodiversity protection, water rights, and resources law.", "aliases": ["climate litigation", "environmental regulation", "water law", "planning law"]},
            "criminology": {"desc": "Theories of offending, victimology, crime prevention, penology, and desistance.", "aliases": ["victimology", "criminological theory", "crime prevention", "desistance", "penology"]},
            "criminal-justice": {"desc": "Policing, court systems, sentencing practices, corrections, parole, and restorative justice.", "aliases": ["policing", "sentencing", "corrections", "courts", "restorative justice", "prisons"]},
            "regulation-and-compliance": {"desc": "Responsive regulation, financial regulation, cyber law, AI governance, and compliance frameworks.", "aliases": ["regulatory governance", "cyber law", "AI regulation", "compliance", "data privacy law"]},
        },
        "systems": {
            "legal-and-court-systems": {"desc": "Supreme courts, appellate courts, tribunals, and arbitral bodies.", "aliases": ["court", "tribunal", "judiciary", "arbitration panel"]},
            "correctional-and-police-agencies": {"desc": "Prisons, police departments, parole boards, and law enforcement agencies.", "aliases": ["police", "prison", "correctional facility", "parole board"]},
            "regulatory-bodies": {"desc": "Financial regulators, competition authorities, and environmental protection agencies.", "aliases": ["regulator", "antitrust authority", "privacy commissioner"]},
            "legal-instruments": {"desc": "Statutes, international conventions, contracts, patents, and judicial precedents.", "aliases": ["statute", "treaty", "judicial precedent", "contract"]},
        },
        "methods": {
            "doctrinal-legal-analysis": {"desc": "Analysis of case law precedents, statutory construction, and legal synthesis.", "aliases": ["doctrinal analysis", "case law analysis", "statutory interpretation"]},
            "empirical-legal-studies": {"desc": "Quantitative court docket analysis, sentencing regression models, and judicial analytics.", "aliases": ["empirical legal", "court data analysis", "sentencing statistics"]},
            "criminological-survey-and-interviews": {"desc": "Victimization surveys, offender interviews, and self-report delinquency scales.", "aliases": ["victimization survey", "offender interview", "self-report survey"]},
            "comparative-legal-methods": {"desc": "Cross-jurisdictional legal comparisons and harmonization analysis.", "aliases": ["comparative law", "cross-jurisdiction"]},
            "socio-legal-fieldwork": {"desc": "Courtroom observation, police ride-alongs, and ethnographic legal studies.", "aliases": ["court observation", "socio-legal", "legal ethnography"]},
        }
    },
    {
        "id": "language-communication-culture",
        "name": "Language, Communication & Culture",
        "category": "Communication & Culture",
        "description": "Covers linguistics, language studies, communication, journalism, media, cultural studies and related research into discourse and information exchange.",
        "sampleTags": ["topic/linguistics", "topic/language", "topic/communication", "topic/media-studies", "topic/cultural-studies"],
        "topics": {
            "linguistics": {"desc": "Phonology, phonetics, syntax, semantics, pragmatics, and morphology.", "aliases": ["syntax", "semantics", "phonetics", "phonology", "morphology", "pragmatics"]},
            "language": {"desc": "Sociolinguistics, language acquisition, bilingualism, historical linguistics, and language endangerment.", "aliases": ["sociolinguistics", "bilingualism", "language revitalization", "historical linguistics"]},
            "communication": {"desc": "Interpersonal communication, organizational communication, strategic PR, and crisis messaging.", "aliases": ["strategic communication", "interpersonal communication", "public relations", "crisis communication"]},
            "media-studies": {"desc": "Broadcasting, platform media, television studies, audience reception, and political economy of media.", "aliases": ["broadcast", "television studies", "audience reception", "media industry"]},
            "journalism": {"desc": "News production, investigative journalism, digital reporting ethics, and misinformation.", "aliases": ["news reporting", "investigative journalism", "misinformation", "journalism ethics", "fact-checking"]},
            "cultural-studies": {"desc": "Popular culture, subcultures, identity politics, postcolonial cultural theory, and globalization.", "aliases": ["popular culture", "cultural theory", "identity politics", "subcultures"]},
            "discourse": {"desc": "Critical discourse analysis (CDA), multimodality, conversation analysis, and semiotics.", "aliases": ["CDA", "semiotics", "multimodality", "conversation analysis", "discourse studies"]},
            "digital-media": {"desc": "Social media algorithms, online communities, digital culture, streaming platforms, and memes.", "aliases": ["social media", "digital culture", "algorithms media", "online community", "streaming"]},
        },
        "systems": {
            "media-platforms-and-outlets": {"desc": "Social platforms (X/TikTok/YouTube), newsrooms, broadcasting networks, and streaming services.", "aliases": ["social media platform", "newsroom", "broadcaster", "streaming service"]},
            "linguistic-corpora": {"desc": "Spoken corpora, written text archives, phonetic recordings, and dictionary databases.", "aliases": ["corpus", "text archive", "phonetic database"]},
            "cultural-audiences": {"desc": "Online fandoms, news consumers, minority language communities, and digital publics.", "aliases": ["fandom", "audience", "speech community", "public sphere"]},
            "communication-campaigns": {"desc": "Public health messaging campaigns, political electoral campaigns, and corporate PR.", "aliases": ["public campaign", "election campaign", "PR campaign"]},
        },
        "methods": {
            "corpus-linguistic-analysis": {"desc": "Concordance analysis, collocation extraction, n-gram frequency, and POS tagging.", "aliases": ["corpus linguistics", "concordance", "collocation", "n-gram"]},
            "conversation-and-discourse-analysis": {"desc": "Jeffersonian transcription, turn-taking analysis, and critical discourse frameworks.", "aliases": ["conversation analysis", "discourse coding", "transcription"]},
            "content-and-framing-analysis": {"desc": "Media framing analysis, quantitative news coding, and thematic media analysis.", "aliases": ["framing analysis", "content coding", "media analysis"]},
            "phonetic-acoustic-analysis": {"desc": "Formant analysis, pitch tracking (Praat), spectrographic measurement, and articulation.", "aliases": ["praat", "formant analysis", "acoustic measurement", "spectrogram"]},
            "digital-ethnography-social-media": {"desc": "Platform data scraping, network analysis of hashtags, and online participant observation.", "aliases": ["social media scraping", "hashtag analysis", "digital ethnography"]},
        }
    },
    {
        "id": "literature-writing",
        "name": "Literature & Writing",
        "category": "Humanities & Literature",
        "description": "Covers literary studies, comparative literature, textual scholarship, rhetoric, creative writing and related analysis of written works.",
        "sampleTags": ["topic/literature", "topic/literary-theory", "topic/comparative-literature", "topic/rhetoric", "topic/creative-writing"],
        "topics": {
            "literature": {"desc": "Poetry, prose fiction, drama, literary periods (Renaissance, Romanticism, Modernism, Postmodernism).", "aliases": ["fiction", "poetry", "drama", "novel", "modernism", "romanticism", "victorian literature"]},
            "literary-theory": {"desc": "Deconstruction, feminist literary theory, ecocriticism, psychoanalytic criticism, and structuralism.", "aliases": ["ecocriticism", "deconstruction", "feminist theory", "narratology", "poststructuralism"]},
            "comparative-literature": {"desc": "World literature, translation studies, intertextuality, and cross-cultural literary influence.", "aliases": ["world literature", "translation studies", "intertextuality", "transnational literature"]},
            "textual-studies": {"desc": "Book history, critical editions, manuscript studies, bibliography, and digital humanities text mining.", "aliases": ["book history", "manuscript studies", "bibliography", "critical edition", "paleography"]},
            "rhetoric": {"desc": "Classical rhetoric, persuasive argumentation, stylistic tropes, and composition studies.", "aliases": ["persuasion", "argumentation", "composition", "classical rhetoric", "stylistics"]},
            "creative-writing": {"desc": "Craft of fiction, poetry poetics, creative non-fiction, memoir, and writing pedagogy.", "aliases": ["poetics", "memoir", "creative non-fiction", "craft of writing", "creative practice"]},
            "narrative": {"desc": "Narratology, story structure, point of view, temporal distortion, and focalization.", "aliases": ["narratology", "storytelling", "narrative structure", "focalization"]},
            "postcolonial-literature": {"desc": "Subaltern voices, diaspora literature, settler-colonial poetics, and indigenous literatures.", "aliases": ["postcolonial", "subaltern", "diaspora literature", "anticolonial"]},
        },
        "systems": {
            "literary-works": {"desc": "Novels, poetic anthologies, playscripts, epic poems, and essays.", "aliases": ["novel", "poem", "play", "anthology", "literary text"]},
            "manuscripts-and-archives": {"desc": "Author manuscripts, letters, drafts, rare book collections, and folios.", "aliases": ["manuscript", "archive", "rare book", "folio"]},
            "literary-movements": {"desc": "Romanticism, Harlem Renaissance, Beat Generation, Magical Realism, and Postmodernism.", "aliases": ["literary movement", "modernist circle", "avant-garde"]},
            "publishing-institutions": {"desc": "Literary magazines, university presses, independent publishers, and book trade networks.", "aliases": ["publisher", "literary journal", "small press"]},
        },
        "methods": {
            "close-reading": {"desc": "Nuanced line-by-line textual interpretation, stylistic analysis, and figurative decoding.", "aliases": ["close reading", "textual interpretation", "stylistic analysis"]},
            "hermeneutic-analysis": {"desc": "Interpretive contextualization, philosophical hermeneutics, and reader-response critique.", "aliases": ["hermeneutics", "reader response", "critical interpretation"]},
            "computational-literary-analysis": {"desc": "Stylometry, topic modeling of corpora, sentiment trajectories, and digital humanities tools.", "aliases": ["stylometry", "distant reading", "topic modeling", "digital humanities"]},
            "archival-textual-editing": {"desc": "Collation of variant editions, stemmatology, and critical apparatus preparation.", "aliases": ["critical editing", "collation", "stemmatology", "archival transcription"]},
            "creative-critical-practice": {"desc": "Exegesis, practitioner reflection, creative craft commentary, and draft iteration.", "aliases": ["creative exegesis", "craft reflection", "practitioner research"]},
        }
    },
    {
        "id": "history-heritage-archaeology",
        "name": "History, Heritage & Archaeology",
        "category": "Historical Studies",
        "description": "Covers historical research, archaeology, heritage, archives, museums, material culture and historical interpretation.",
        "sampleTags": ["topic/history", "topic/archaeology", "topic/heritage", "topic/historiography", "topic/material-culture"],
        "topics": {
            "history": {"desc": "Ancient, medieval, early modern, modern, and contemporary history across global regions.", "aliases": ["modern history", "ancient history", "medieval history", "social history", "political history"]},
            "archaeology": {"desc": "Excavation, bioarchaeology, zooarchaeology, geoarchaeology, and prehistoric settlements.", "aliases": ["excavation", "bioarchaeology", "zooarchaeology", "radiocarbon", "lithics", "prehistory"]},
            "heritage": {"desc": "Cultural heritage management, UNESCO sites, intangible heritage, and monument conservation.", "aliases": ["cultural heritage", "UNESCO", "monument", "conservation heritage", "intangible heritage"]},
            "archives": {"desc": "Archival science, historical records management, manuscript appraisal, and provenance.", "aliases": ["archival science", "records management", "provenance", "historical records"]},
            "museum-studies": {"desc": "Curatorship, exhibition design, restitution of antiquities, and museum visitorship.", "aliases": ["curation", "exhibition", "museums", "restitution", "museology"]},
            "material-culture": {"desc": "Historical artifacts, commodities, textiles, everyday objects, and sensory history.", "aliases": ["artifact", "everyday objects", "material culture", "sensory history"]},
            "historiography": {"desc": "Historical methodology, philosophy of history, archival turns, and schools of historical thought.", "aliases": ["historical method", "philosophy of history", "annales school", "historiographical"]},
            "oral-history": {"desc": "Personal testimonies, oral narratives, survivor accounts, and community memory.", "aliases": ["oral testimony", "life history", "memory studies", "oral history"]},
        },
        "systems": {
            "archaeological-sites": {"desc": "Excavation trenches, burial mounds, rock shelters, ancient cities, and shipwrecks.", "aliases": ["archaeological site", "trench", "shipwreck", "burial mound"]},
            "archival-collections": {"desc": "State archives, church registries, diplomatic dispatches, and private correspondence.", "aliases": ["state archive", "registry", "correspondence archive"]},
            "historical-societies": {"desc": "Empires, dynasties, peasant communities, industrial towns, and trade guilds.", "aliases": ["empire", "dynasty", "guild", "historical society"]},
            "museum-collections": {"desc": "Antiquities galleries, specimen repositories, and memorial monuments.", "aliases": ["museum collection", "antiquities", "monument"]},
        },
        "methods": {
            "archival-document-analysis": {"desc": "Primary source paleography, critical source criticism, and document contextualization.", "aliases": ["primary source analysis", "paleography", "source criticism", "archival research"]},
            "archaeological-excavation": {"desc": "Stratigraphic excavation, Harris matrix recording, and spatial artifact mapping.", "aliases": ["stratigraphy", "harris matrix", "excavation", "artifact recording"]},
            "radiometric-and-dating-methods": {"desc": "Carbon-14 (C14) dating, dendrochronology, thermoluminescence, and isotope sourcing.", "aliases": ["C14 dating", "dendrochronology", "thermoluminescence", "radiometric dating"]},
            "oral-history-interviewing": {"desc": "Semi-structured biographical interviews, audio transcription, and narrative analysis.", "aliases": ["oral history interview", "narrative analysis", "biographical interview"]},
            "spatial-historical-gis": {"desc": "Historical GIS mapping, aerial lidar survey for archaeology, and viewshed analysis.", "aliases": ["historical GIS", "lidar archaeology", "viewshed analysis"]},
        }
    },
    {
        "id": "philosophy-ethics-religious",
        "name": "Philosophy, Ethics & Religious Studies",
        "category": "Philosophy & Religion",
        "description": "Covers philosophy, logic, epistemology, metaphysics, ethics, philosophy of science, religious studies and theology.",
        "sampleTags": ["topic/philosophy", "topic/ethics", "topic/epistemology", "topic/logic", "topic/philosophy-of-science"],
        "topics": {
            "philosophy": {"desc": "Analytic/continental philosophy, history of philosophy, aesthetics, and political philosophy.", "aliases": ["analytic philosophy", "continental philosophy", "political philosophy", "aesthetics"]},
            "ethics": {"desc": "Normative ethics (utilitarianism, deontology, virtue ethics), metaethics, and applied ethics.", "aliases": ["normative ethics", "applied ethics", "metaethics", "virtue ethics", "deontology", "bioethics"]},
            "epistemology": {"desc": "Theory of knowledge, justified true belief, skepticism, epistemic injustice, and Bayesian epistemology.", "aliases": ["theory of knowledge", "epistemic injustice", "skepticism", "justification", "bayesian epistemology"]},
            "metaphysics": {"desc": "Ontology, modality, causation, time, personal identity, and philosophy of mind.", "aliases": ["ontology", "modality", "causation", "philosophy of mind", "consciousness"]},
            "logic": {"desc": "Formal logic, modal logic, mathematical logic, non-classical logic, and argumentation.", "aliases": ["formal logic", "modal logic", "proof theory", "non-classical logic", "syllogism"]},
            "philosophy-of-science": {"desc": "Scientific realism, reductionism, demarcation, explanation, and philosophy of physics/biology.", "aliases": ["scientific realism", "demarcation", "philosophy of physics", "scientific explanation"]},
            "religion": {"desc": "Comparative religion, sociology of religion, religious ritual, and secularization.", "aliases": ["comparative religion", "sociology of religion", "religious ritual", "secularization"]},
            "theology": {"desc": "Systematic theology, biblical hermeneutics, doctrinal history, and interfaith dialogue.", "aliases": ["systematic theology", "hermeneutics", "scriptural exegesis", "doctrine"]},
        },
        "systems": {
            "philosophical-traditions": {"desc": "Analytic, phenomenology, existentialism, pragmatism, and Eastern philosophical traditions.", "aliases": ["analytic tradition", "phenomenology", "pragmatism", "buddhism", "stoicism"]},
            "ethical-frameworks": {"desc": "Kantian deontology, utilitarian maximization, virtue ethics, and care ethics.", "aliases": ["utilitarianism", "kantian", "virtue ethics", "ethics of care"]},
            "religious-traditions": {"desc": "Christianity, Islam, Judaism, Buddhism, Hinduism, and indigenous spiritualities.", "aliases": ["christianity", "islam", "judaism", "buddhism", "hinduism"]},
            "conceptual-systems": {"desc": "Formal axiomatic systems, metaphysical models, and epistemological frameworks.", "aliases": ["axiomatic system", "ontology model", "formal framework"]},
        },
        "methods": {
            "conceptual-analysis": {"desc": "Thought experiments, counterexample formulation, and logical definition dissection.", "aliases": ["thought experiment", "counterexample", "conceptual analysis"]},
            "formal-logical-proof": {"desc": "Model-theoretic proofs, natural deduction derivations, and semantic tableau methods.", "aliases": ["formal proof", "natural deduction", "model theory", "tableau"]},
            "historical-philosophical-reconstruction": {"desc": "Exegesis of historical philosophical texts and contextual philosophical argument analysis.", "aliases": ["textual exegesis", "philosophical history", "textual reconstruction"]},
            "scriptural-exegesis": {"desc": "Historical-critical biblical exegesis, linguistic translation, and theological commentary.", "aliases": ["biblical exegesis", "historical-critical", "scriptural commentary"]},
            "normative-ethical-argumentation": {"desc": "Applied ethical reasoning, reflective equilibrium, and moral dilemma resolution.", "aliases": ["reflective equilibrium", "moral reasoning", "ethical analysis"]},
        }
    },
    {
        "id": "creative-arts-design",
        "name": "Creative Arts & Design",
        "category": "Creative Arts & Design",
        "description": "Covers visual art, music, performing arts, screen media, design practice, art theory and creative research.",
        "sampleTags": ["topic/visual-arts", "topic/music", "topic/performing-arts", "topic/design", "topic/creative-practice"],
        "topics": {
            "visual-arts": {"desc": "Painting, sculpture, printmaking, contemporary installation art, and photography.", "aliases": ["painting", "sculpture", "installation art", "photography", "contemporary art"]},
            "music": {"desc": "Music composition, musicology, performance practice, ethnomusicology, and acoustic design.", "aliases": ["composition", "musicology", "ethnomusicology", "performance practice", "sound art"]},
            "performing-arts": {"desc": "Theater, contemporary dance, choreography, acting technique, and live performance studies.", "aliases": ["theatre", "dance", "choreography", "performance studies", "acting"]},
            "film": {"desc": "Cinema studies, screenwriting, cinematography, documentary film, and film theory.", "aliases": ["cinema", "screenwriting", "cinematography", "documentary", "film theory"]},
            "design": {"desc": "Industrial design, interaction design, graphic communication, design thinking, and typography.", "aliases": ["industrial design", "interaction design", "graphic design", "typography", "design thinking"]},
            "art-history": {"desc": "Art criticism, iconography, artistic movements (Modernism, Baroque, Avant-garde), and provenance.", "aliases": ["art criticism", "iconography", "modern art", "baroque", "avant-garde"]},
            "digital-media": {"desc": "Interactive digital art, virtual reality (VR), generative art, game design, and sonic arts.", "aliases": ["digital art", "virtual reality", "VR", "generative art", "game design", "creative coding"]},
            "creative-practice": {"desc": "Practice-led research, studio methodology, creative pedagogy, and artist-researcher reflexivity.", "aliases": ["practice-led research", "studio practice", "artistic research", "creative methodology"]},
        },
        "systems": {
            "artworks-and-installations": {"desc": "Paintings, sculptures, gallery installations, musical scores, and cinematic releases.", "aliases": ["artwork", "installation", "musical score", "film release"]},
            "performance-venues": {"desc": "Theaters, concert halls, public art sites, and black-box studios.", "aliases": ["theatre", "concert hall", "gallery", "studio"]},
            "design-artifacts": {"desc": "Physical product prototypes, software UI interfaces, and visual identity systems.", "aliases": ["prototype", "UI design", "visual identity"]},
            "creative-technologies": {"desc": "Synthesizers, digital audio workstations (DAWs), game engines (Unity/Unreal), and 3D renderers.", "aliases": ["DAW", "game engine", "unity", "blender", "synthesizer"]},
        },
        "methods": {
            "practice-led-research": {"desc": "Studio-based creative exploration, reflective practitioner logs, and artistic prototyping.", "aliases": ["practice-led", "artistic research", "studio methodology"]},
            "formal-aesthetic-critique": {"desc": "Formal analysis of composition, color theory, harmonic progression, and dramaturgical structure.", "aliases": ["aesthetic analysis", "formal critique", "harmonic analysis", "dramaturgy"]},
            "performance-analysis": {"desc": "Video choreography annotation, movement capture, and live performance documentation.", "aliases": ["choreographic analysis", "movement analysis", "performance documentation"]},
            "design-ethnography": {"desc": "User co-design workshops, contextual inquiry, and prototype iteration testing.", "aliases": ["co-design", "design ethnography", "prototype testing"]},
            "art-historical-provenance": {"desc": "Archival attribution, conservation material science, and exhibition history analysis.", "aliases": ["provenance research", "attribution", "conservation analysis"]},
        }
    },
    {
        "id": "indigenous-studies",
        "name": "Indigenous Studies",
        "category": "Indigenous Studies",
        "description": "Covers research concerning Indigenous peoples, cultures, languages, knowledges, methodologies, health, education, environments and communities globally.",
        "sampleTags": ["topic/indigenous-knowledge", "topic/indigenous-methodologies", "topic/indigenous-health", "topic/indigenous-governance", "topic/decolonial-research"],
        "topics": {
            "indigenous-knowledge": {"desc": "Traditional ecological knowledge (TEK), cultural heritage, oral traditions, and epistemologies.", "aliases": ["traditional ecological knowledge", "TEK", "indigenous epistemology", "customary knowledge", "songlines"]},
            "indigenous-methodologies": {"desc": "Decolonial research paradigms, Indigenous research sovereignty, reciprocity, and ethical protocols.", "aliases": ["decolonial methodology", "indigenous research protocols", "relational accountability", "yarning"]},
            "indigenous-health": {"desc": "Culturally safe healthcare, holistic health models, social determinants of Indigenous wellbeing.", "aliases": ["cultural safety", "indigenous wellbeing", "closing the gap", "holistic health"]},
            "indigenous-education": {"desc": "Two-way education, Indigenous pedagogical frameworks, language immersion, and community schooling.", "aliases": ["two-way learning", "bilingual education", "indigenous pedagogy", "cultural immersion"]},
            "indigenous-governance": {"desc": "Native title, self-determination, treaty making, customary law, and community leadership.", "aliases": ["native title", "self-determination", "treaty", "customary law", "indigenous sovereignty"]},
            "indigenous-language": {"desc": "Indigenous language documentation, linguistic revitalization, mother-tongue preservation, and dictionaries.", "aliases": ["language revitalization", "indigenous linguistics", "endangered languages", "mother tongue"]},
            "decolonial-research": {"desc": "Decolonizing institutions, anti-colonial critique, archival repatriation, and land back movements.", "aliases": ["decolonization", "anticolonial", "repatriation", "land back", "decolonial theory"]},
            "land-and-sea-management": {"desc": "Caring for Country, cultural burning/fire management, ranger programs, and customary tenure.", "aliases": ["caring for country", "cultural burning", "indigenous ranger", "sea country", "customary tenure"]},
        },
        "systems": {
            "indigenous-communities": {"desc": "First Nations communities, tribal councils, land councils, and urban Indigenous collectives.", "aliases": ["first nations", "tribal council", "land council", "indigenous community"]},
            "country-and-ancestral-lands": {"desc": "Traditional lands, sea country, sacred sites, and cultural landscapes.", "aliases": ["country", "ancestral land", "sea country", "sacred site"]},
            "cultural-expressions": {"desc": "Ceremonial practices, songlines, Indigenous art traditions, and material heritage.", "aliases": ["songlines", "ceremony", "indigenous art", "cultural practice"]},
            "indigenous-organizations": {"desc": "Aboriginal community-controlled health organizations (ACCHOs), native title bodies, and treaty commissions.", "aliases": ["ACCHO", "native title body", "treaty commission", "indigenous organization"]},
        },
        "methods": {
            "yarning-and-oral-storywork": {"desc": "Yarning methodologies, oral history circles, and narrative storywork with Elders.", "aliases": ["yarning", "storywork", "dadirri", "oral history indigenous"]},
            "community-led-participatory-research": {"desc": "Co-designed research, community consent protocols (OACAP/FPIC), and benefit-sharing frameworks.", "aliases": ["FPIC", "community-led", "participatory research", "OACAP", "co-design"]},
            "linguistic-language-documentation": {"desc": "Phonetic recording of Elders, orthography development, and participatory dictionary making.", "aliases": ["language documentation", "audio recording elders", "dictionary compiling"]},
            "cultural-mapping-and-gis": {"desc": "Indigenous spatial mapping, sacred site recording, and country monitoring.", "aliases": ["cultural mapping", "indigenous GIS", "country monitoring"]},
            "decolonial-policy-critique": {"desc": "Structural critique of government policy, legislative analysis, and self-determination benchmarking.", "aliases": ["policy critique", "self-determination assessment", "rights-based analysis"]},
        }
    }
]

def generate_profile_yaml(p_data):
    lines = []
    lines.append('schema_version: 1')
    lines.append('version: "1.0.0"')
    lines.append('')
    lines.append('description: >')
    lines.append(f'  {p_data["description"]}')
    lines.append('')
    lines.append('conventions:')
    lines.append('  separator: "/"')
    lines.append('  canonical_tag_format: "{namespace}/{value}"')
    lines.append('  allow_unlisted_values: false')
    lines.append('  prefer_precision_over_recall: true')
    lines.append('  avoid_metadata_duplication: true')
    lines.append('  metadata_fields_not_to_tag:')
    lines.append('    - author')
    lines.append('    - journal')
    lines.append('    - year')
    lines.append('    - doi')
    lines.append('    - publisher')
    lines.append('    - institution')
    lines.append('  notes:')
    lines.append('    - "Collections/folders organize projects; tags reflect intrinsic content."')
    lines.append('    - "Role describes contribution style (empirical, theoretical, review, method)."')
    lines.append('    - "Topic describes substantive domain questions, phenomena, or theories."')
    lines.append('    - "System describes the physical, biological, conceptual, or social entity investigated."')
    lines.append('    - "Method describes specific investigative techniques, protocols, or models."')
    lines.append('    - "Status and priority are human-managed workflow namespaces."')
    lines.append('')
    lines.append('classifier:')
    lines.append('  semantic_namespaces:')
    lines.append('    - role')
    lines.append('    - topic')
    lines.append('    - system')
    lines.append('    - method')
    lines.append('  workflow_namespaces:')
    lines.append('    - status')
    lines.append('  human_only_namespaces:')
    lines.append('    - priority')
    lines.append('  rules:')
    lines.append('    - "Never invent a tag not defined in this taxonomy."')
    lines.append('    - "Do not tag a concept merely because it is mentioned in passing."')
    lines.append('    - "Prefer the most specific applicable canonical tag without adding redundant synonyms."')
    lines.append('    - "Do not infer priority or reading status from document content."')
    lines.append('    - "Use aliases only for recognition and normalisation; always emit the canonical tag."')
    lines.append('')
    lines.append('relationships: []')
    lines.append('')
    lines.append('namespaces:')
    lines.append('')
    lines.append('  status:')
    lines.append('    description: "Reading and processing workflow state."')
    lines.append('    kind: workflow')
    lines.append('    classifier_eligible: false')
    lines.append('    max_tags: 1')
    lines.append('    mutually_exclusive: true')
    lines.append('    user_managed:')
    lines.append('      - reading')
    lines.append('      - read')
    lines.append('      - processed')
    lines.append('    values:')
    lines.append('      needs-triage:')
    lines.append('        description: "Item requires human review or candidate tags await confirmation."')
    lines.append('        aliases: ["triage", "needs review", "needs-review"]')
    lines.append('      to-read:')
    lines.append('        description: "Item has been queued into the reading list."')
    lines.append('        aliases: ["unread", "to read", "to_read"]')
    lines.append('      reading:')
    lines.append('        description: "Item is actively being read."')
    lines.append('      read:')
    lines.append('        description: "Item has been read and understood."')
    lines.append('        aliases: ["done"]')
    lines.append('      processed:')
    lines.append('        description: "Notes or knowledge have been extracted into broader research workflow."')
    lines.append('')
    lines.append('  priority:')
    lines.append('    description: "User judgement about importance or urgency to revisit."')
    lines.append('    kind: judgement')
    lines.append('    classifier_eligible: false')
    lines.append('    max_tags: 2')
    lines.append('    values:')
    lines.append('      core:')
    lines.append('        description: "Foundational reference essential to ongoing projects."')
    lines.append('        aliases: ["essential", "seminal", "must-read", "foundational"]')
    lines.append('      high:')
    lines.append('        description: "Highly relevant paper containing important results or techniques."')
    lines.append('        aliases: ["important", "key-reference"]')
    lines.append('      revisit:')
    lines.append('        description: "Contains specific derivations, tables, or parameters to revisit later."')
    lines.append('        aliases: ["bookmark", "check-later", "reference-back"]')
    lines.append('')
    lines.append('  role:')
    lines.append('    description: "Contribution style or epistemic purpose the work serves in the literature."')
    lines.append('    kind: semantic')
    lines.append('    classifier_eligible: true')
    lines.append('    max_tags: 2')
    lines.append('    values:')
    lines.append('      review:')
    lines.append('        description: "Synthesises an established body of literature rather than presenting only a single narrow result."')
    lines.append('        aliases: ["review article", "survey", "overview", "systematic review", "meta-analysis"]')
    lines.append('      empirical:')
    lines.append('        description: "Presents primary empirical data, field/laboratory observations, or experimental measurements."')
    lines.append('        aliases: ["experimental", "empirical study", "measurement", "observational study"]')
    lines.append('      theoretical:')
    lines.append('        description: "Develops formal analytical theory, mathematical derivations, or conceptual frameworks."')
    lines.append('        aliases: ["theory", "analytical model", "conceptual framework", "formal derivation"]')
    lines.append('      methodological:')
    lines.append('        description: "Introduces or evaluates a new algorithm, experimental protocol, measurement tool, or analytical workflow."')
    lines.append('        aliases: ["methodology", "algorithm development", "protocol", "new method"]')
    lines.append('      computational:')
    lines.append('        description: "Presents numerical simulations, scientific computing models, or computational software tools."')
    lines.append('        aliases: ["simulation", "in silico", "numerical study", "computational model"]')
    lines.append('      application:')
    lines.append('        description: "Applies established methodologies to investigate a specific domain target or practical case study."')
    lines.append('        aliases: ["case study", "applied study", "field application"]')
    lines.append('      commentary:')
    lines.append('        description: "Editorial, commentary, position paper, or perspective on field directions."')
    lines.append('        aliases: ["perspective", "editorial", "position paper", "opinion"]')
    lines.append('')
    lines.append('  topic:')
    lines.append('    description: "Substantive domain phenomena, research questions, theories, or mechanisms."')
    lines.append('    kind: semantic')
    lines.append('    classifier_eligible: true')
    lines.append('    max_tags: 4')
    lines.append('    values:')
    for t_key, t_val in p_data["topics"].items():
        lines.append(f'      {t_key}:')
        lines.append(f'        description: "{t_val["desc"]}"')
        aliases_str = ", ".join(f'"{a}"' for a in t_val["aliases"])
        lines.append(f'        aliases: [{aliases_str}]')
    lines.append('')
    lines.append('  system:')
    lines.append('    description: "Physical, biological, social, or computational entity under primary study."')
    lines.append('    kind: semantic')
    lines.append('    classifier_eligible: true')
    lines.append('    max_tags: 3')
    lines.append('    values:')
    for s_key, s_val in p_data["systems"].items():
        lines.append(f'      {s_key}:')
        lines.append(f'        description: "{s_val["desc"]}"')
        aliases_str = ", ".join(f'"{a}"' for a in s_val["aliases"])
        lines.append(f'        aliases: [{aliases_str}]')
    lines.append('')
    lines.append('  method:')
    lines.append('    description: "Investigative, computational, analytical, or experimental techniques applied."')
    lines.append('    kind: semantic')
    lines.append('    classifier_eligible: true')
    lines.append('    max_tags: 3')
    lines.append('    values:')
    for m_key, m_val in p_data["methods"].items():
        lines.append(f'      {m_key}:')
        lines.append(f'        description: "{m_val["desc"]}"')
        aliases_str = ", ".join(f'"{a}"' for a in m_val["aliases"])
        lines.append(f'        aliases: [{aliases_str}]')
    lines.append('')

    return "\n".join(lines)

def main():
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "examples" / "taxonomies" / "profiles"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean old profiles
    for p_file in out_dir.glob("*.yml"):
        p_file.unlink()

    generated = {}
    for p in PROFILES_DATA:
        filename = f"{p['id']}.yml"
        filepath = out_dir / filename
        yaml_content = generate_profile_yaml(p)
        filepath.write_text(yaml_content, encoding="utf-8")
        # Validate with Python Taxonomy
        tax = load_taxonomy(filepath)
        generated[p["id"]] = {
            "name": p["name"],
            "category": p["category"],
            "description": p["description"],
            "sampleTags": p["sampleTags"],
            "yaml": yaml_content,
            "tagCount": len(tax.classifier_tags()),
            "namespaceCount": len(tax.namespaces)
        }
        print(f"✓ Generated {p['id']}.yml: {len(tax.classifier_tags())} tags")

    print(f"\nAll {len(generated)} profiles generated and validated with Python Taxonomy!")

if __name__ == "__main__":
    main()
