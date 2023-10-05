import numpy as np
from Bio import SeqIO
from uuid import uuid4


# Module imports
from primal_digest.classes import FKmer, RKmer, PrimerPair
from primal_digest.seq_functions import remove_end_insertion
from primal_digest.digestion import (
    digest,
    generate_valid_primerpairs,
)
from primal_digest.mapping import create_mapping


class MSA:
    # Provided
    name: str
    path: str
    msa_index: int
    array: np.ndarray

    # Calculated on init
    _uuid: str
    _chrom_name: str  # only used in the primer.bed file and html report
    _mapping_array: np.ndarray | None

    # Calculated on evaluation
    fkmers: list[FKmer]
    rkmers: list[RKmer]
    primerpairs: list[PrimerPair]

    def __init__(self, name, path, msa_index, mapping) -> None:
        self.name = name
        self.path = str(path)
        self.msa_index = msa_index

        # Read in the MSA
        records_index = SeqIO.index(self.path, "fasta")
        self.array = np.array(
            [record.seq.upper() for record in records_index.values()], dtype="U1"
        )
        self.array = remove_end_insertion(self.array)

        # Create the mapping array
        if mapping == "consensus":
            self._mapping_array = None
            self._chrom_name = self.name
        elif mapping == "first":
            self._mapping_array, self.array = create_mapping(self.array, 0)
            self._chrom_name = list(records_index)[0]

        # Asign a UUID
        self._uuid = str(uuid4())[:8]

    def digest(self, cfg):
        self.fkmers, self.rkmers = digest(
            msa_array=self.array,
            cfg=cfg,
        )
        # remap the fkmer and rkmers if needed
        if self._mapping_array is not None:
            self.fkmers = [fkmer.remap(self._mapping_array) for fkmer in self.fkmers]
            self.fkmers = [x for x in self.fkmers if x is not None]
            self.rkmers = [rkmer.remap(self._mapping_array) for rkmer in self.rkmers]
            self.rkmers = [x for x in self.rkmers if x is not None]

    def generate_primerpairs(self, cfg):
        self.primerpairs = generate_valid_primerpairs(
            self.fkmers,
            self.rkmers,
            cfg,
            self.msa_index,
        )
