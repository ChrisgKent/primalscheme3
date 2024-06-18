# Module imports
from primaldimer_py import Kmer, do_pools_interact_py  # type: ignore

from primalscheme3.core.mismatches import MatchDB
from primalscheme3.core.thermo import calc_tm


class FKmer(Kmer):
    end: int
    # Add slots for some performance gains
    __slots__ = ["end", "_starts"]

    def __init__(self, end, seqs) -> None:
        self.end = end

    def len(self) -> list[int]:
        return self.lens()

    def starts(self) -> set[int]:
        return {self.end - x for x in self.lens()}

    def __str__(self, reference, amplicon_prefix, pool) -> str:
        string_list = []
        for i, seq in enumerate(sorted(self.seqs), 1):
            string_list.append(
                f"{reference}\t{self.end-len(seq)}\t{self.end}\t{amplicon_prefix}_LEFT_{i}\t{pool}\t+\t{seq}\n"
            )
        return "".join(string_list)

    def find_matches(
        self,
        matchDB: MatchDB,
        remove_expected: bool,
        fuzzy: bool,
        kmersize: int,
        msa_index,
    ) -> set[tuple]:
        """Returns all matches of this FKmer"""
        return matchDB.find_fkmer(
            self,
            fuzzy=fuzzy,
            remove_expected=remove_expected,
            kmersize=kmersize,
            msaindex=msa_index,
        )

    def __hash__(self) -> int:
        seqs = list(self.seqs)
        seqs.sort()
        return hash(f"{self.end}{self.seqs}")

    def __eq__(self, other):
        if isinstance(other, FKmer):
            return self.__hash__() == other.__hash__()
        else:
            return False

    def remap(self, mapping_array):
        """
        Remaps the fkmer to a new indexing system
        Returns None if the fkmer is not valid
        """
        if mapping_array[self.end] is not None:
            self.end = mapping_array[self.end]
            self._starts = {self.end - len(x) for x in self.seqs}
            return self
        else:
            return None


class RKmer(Kmer):
    start: int

    # Add slots for some performance gains
    __slots__ = ["start", "_ends"]

    def __init__(self, start, seqs) -> None:
        self.start = start

    def len(self) -> list[int]:
        return self.lens()

    def ends(self) -> set[int]:
        return {x + self.start for x in self.lens()}

    def __str__(self, reference, amplicon_prefix, pool) -> str:
        string_list = []
        for i, seq in enumerate(sorted(self.seqs), 1):
            string_list.append(
                f"{reference}\t{self.start}\t{self.start+len(seq)}\t{amplicon_prefix}_RIGHT_{i}\t{pool}\t-\t{seq}\n"
            )
        return "".join(string_list)

    def find_matches(
        self,
        matchDB: MatchDB,
        remove_expected: bool,
        fuzzy: bool,
        kmersize: int,
        msa_index: int,
    ) -> set[tuple]:
        """Returns all matches of this FKmer"""
        return matchDB.find_rkmer(
            self,
            fuzzy=fuzzy,
            remove_expected=remove_expected,
            kmersize=kmersize,
            msaindex=msa_index,
        )

    def __hash__(self) -> int:
        seqs = list(self.seqs)
        seqs.sort()
        return hash(f"{self.start}{self.seqs}")

    def __eq__(self, other):
        if isinstance(other, RKmer):
            return self.__hash__() == other.__hash__()
        else:
            return False

    def remap(self, mapping_array):
        """
        Remaps the rkmer to a new indexing system
        Returns None if the rkmer is not valid
        """
        if mapping_array[self.start] is not None:
            self.start = mapping_array[self.start]
            self._ends = {len(x) + self.start for x in self.seqs}
            return self
        else:
            return None


class PrimerPair:
    fprimer: FKmer
    rprimer: RKmer
    amplicon_number: int
    pool: int
    msa_index: int
    chrom_name: str | None
    amplicon_prefix: str | None

    __slots__ = [
        "fprimer",
        "rprimer",
        "amplicon_number",
        "pool",
        "msa_index",
        "chrom_name",
        "amplicon_prefix",
    ]

    def __init__(
        self,
        fprimer,
        rprimer,
        msa_index,
        amplicon_number=-1,
        pool=-1,
    ):
        self.fprimer = fprimer
        self.rprimer = rprimer
        self.amplicon_number = amplicon_number
        self.pool = pool
        self.msa_index = msa_index
        self.chrom_name = None
        self.amplicon_prefix = None

    def set_amplicon_number(self, amplicon_number) -> None:
        self.amplicon_number = amplicon_number

    def set_pool_number(self, pool_number) -> None:
        self.amplicon_number = pool_number

    def find_matches(self, matchDB, fuzzy, remove_expected, kmersize) -> set[tuple]:
        """
        Find matches for the FKmer and RKmer
        """
        matches = set()
        # Find the FKmer matches
        matches.update(
            self.fprimer.find_matches(
                matchDB, fuzzy, remove_expected, kmersize, msa_index=self.msa_index
            )
        )
        # Find the RKmer matches
        matches.update(
            self.rprimer.find_matches(
                matchDB, fuzzy, remove_expected, kmersize, self.msa_index
            )
        )
        return matches

    def kmers(self):
        """
        Returns the FKmer and RKmer
        """
        return self.fprimer, self.rprimer

    def primertrimmed_region(self) -> tuple[int, int]:
        """
        Returns the region of the primertrimed region
        """
        return self.fprimer.end, self.rprimer.start - 1

    @property
    def start(self) -> int:
        return min(self.fprimer.starts())

    @property
    def end(self) -> int:
        return max(self.rprimer.ends())

    def inter_free(self, cfg) -> bool:
        """
        True means interaction
        """
        return do_pools_interact_py(
            [*self.fprimer.seqs], [*self.rprimer.seqs], cfg["dimerscore"]
        )

    def all_seqs(self) -> list[str]:
        return [x for x in self.fprimer.seqs] + [x for x in self.rprimer.seqs]

    def calc_tm(self, cfg) -> list[float]:
        """
        Calculates the tm for all primers in the PrimerPair
        :param cfg: config dict
        :return: list of tm values
        """
        return [calc_tm(seq, cfg) for seq in self.all_seqs()]

    def __hash__(self) -> int:
        return hash(f"{self.start}{self.end}{self.all_seqs()}")

    def __eq__(self, other):
        if isinstance(other, PrimerPair):
            return self.__hash__() == other.__hash__()
        else:
            return False

    def to_bed(self) -> str:
        """
        Turns the primerpair into a string for a bed file
        :param chromname: name of the chromosome
        :param amplicon_prefix: prefix for the amplicon
        :return: string for the bed file
        """
        return self.__str__()

    def __str__(self):
        return self.fprimer.__str__(
            reference=f"{self.chrom_name}",
            amplicon_prefix=f"{self.amplicon_prefix}_{self.amplicon_number}",
            pool=self.pool + 1,
        ) + self.rprimer.__str__(
            reference=f"{self.chrom_name}",
            amplicon_prefix=f"{self.amplicon_prefix}_{self.amplicon_number}",
            pool=self.pool + 1,
        )
