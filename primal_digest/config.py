class Cfg:
    amplicon_size_min = 360
    amplicon_size_max = 400
    min_overlap = 20
    mv_conc = 100.0
    dv_conc = 2.0
    dntp_conc = 0.8
    dna_conc = 15.0
    dimer_max_tm = -10.0
    dimer_min_identity = 0.8
    primer_gc_min = 30
    primer_gc_max = 55
    primer_tm_min = 59.5
    primer_tm_max = 62.5
    primer_homopolymer_max = 5
    primer_hairpin_th_max = 47.0


config_dict = {
    "msa_checksums": [],
    "msa_paths": [],
    "refname": "msa",
    "n_cores": 1,
    "output_prefix": "output",
}

thermo_config = {
    "amplicon_size_min": 360,
    "amplicon_size_max": 400,
    "min_overlap": 20,
    "mv_conc": 100.0,
    "dv_conc": 2.0,
    "dntp_conc": 0.8,
    "dna_conc": 15.0,
    "dimer_max_tm": -10.0,
    "dimer_min_identity": 0.8,
    "primer_gc_min": 30,
    "primer_gc_max": 55,
    "primer_tm_min": 59.5,
    "primer_tm_max": 62.5,
    "primer_homopolymer_max": 5,
    "primer_hairpin_th_max": 47.0,
}


AMBIGUOUS_DNA = {
    "M": "AC",
    "R": "AG",
    "W": "AT",
    "S": "CG",
    "Y": "CT",
    "K": "GT",
    "V": "ACG",
    "H": "ACT",
    "D": "AGT",
    "B": "CGT",
}
ALL_DNA = {
    "A": "A",
    "C": "C",
    "G": "G",
    "T": "T",
    "M": "AC",
    "R": "AG",
    "W": "AT",
    "S": "CG",
    "Y": "CT",
    "K": "GT",
    "V": "ACG",
    "H": "ACT",
    "D": "AGT",
    "B": "CGT",
}
AMBIGUOUS_DNA_COMPLEMENT = {
    "A": "T",
    "C": "G",
    "G": "C",
    "T": "A",
    "M": "K",
    "R": "Y",
    "W": "W",
    "S": "S",
    "Y": "R",
    "K": "M",
    "V": "B",
    "H": "D",
    "D": "H",
    "B": "V",
    "X": "X",
    "N": "N",
}
