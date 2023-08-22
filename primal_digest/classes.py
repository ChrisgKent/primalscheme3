from primaldimer_py import do_pools_interact_py

import abc
import re

# Module imports
from primal_digest.primer_pair_score import ol_pp_score, walk_pp_score
from primal_digest.seq_functions import expand_ambs, reverse_complement
from primal_digest.config import AMBIGUOUS_DNA_COMPLEMENT
from primal_digest.mismatches import MatchDB, detect_new_products

REGEX_PATTERN_PRIMERNAME = re.compile("\d+(_RIGHT|_LEFT|_R|_L)")


def re_primer_name(string) -> tuple[str, str] | None:
    """
    Will return (amplicon_number, R/L) or None
    """
    match = REGEX_PATTERN_PRIMERNAME.search(string)
    if match:
        return match.group().split("_")
    return None


class FKmer:
    end: int
    seqs: set[str]
    _starts: set[int]

    def __init__(self, end, seqs) -> None:
        self.end = end
        self.seqs = seqs
        self._starts = {self.end - len(x) for x in self.seqs}

    def len(self) -> set[int]:
        return {len(x) for x in self.seqs}

    def starts(self) -> set[int]:
        return self._starts

    def __str__(self, referance, amplicon_prefix, pool) -> str:
        string_list = []
        counter = 0
        seqs = list(self.seqs)
        seqs.sort()
        for seq in seqs:
            string_list.append(
                f"{referance}\t{self.end-len(seq)}\t{self.end}\t{amplicon_prefix}_LEFT_{counter}\t{pool}\t+\t{seq}\n"
            )
            counter += 1
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


class RKmer:
    start: int
    seqs: set[str]
    _ends: set[int]

    def __init__(self, start, seqs) -> None:
        self.start = start
        self.seqs = seqs
        self._ends = {len(x) + self.start for x in self.seqs}

    def len(self) -> set[int]:
        return {len(x) for x in self.seqs}

    def ends(self) -> set[int]:
        return self._ends

    def __str__(self, referance, amplicon_prefix, pool) -> str:
        string_list = []
        counter = 0
        seqs = list(self.seqs)
        seqs.sort()
        for seq in seqs:
            string_list.append(
                f"{referance}\t{self.start}\t{self.start+len(seq)}\t{amplicon_prefix}_RIGHT_{counter}\t{pool}\t-\t{seq}\n"
            )
            counter += 1
        return "".join(string_list)

    def reverse_complement(self) -> set[str]:
        return {reverse_complement(x) for x in self.seqs}

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


class PrimerPair:
    fprimer: FKmer
    rprimer: RKmer
    amplicon_number: int
    pool: int
    msa_index: int

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
            self.fprimer.seqs, self.rprimer.seqs, cfg["dimerscore"]
        )

    def all_seqs(self) -> set[str]:
        return [x for x in self.fprimer.seqs] + [x for x in self.rprimer.seqs]

    def __hash__(self) -> int:
        return hash(f"{self.start}{self.end}{self.all_seqs()}")

    def __str__(self, ref_name, amplicon_prefix):
        return self.fprimer.__str__(
            referance=f"{ref_name}",
            amplicon_prefix=f"{amplicon_prefix}_{self.amplicon_number}",
            pool=self.pool + 1,
        ) + self.rprimer.__str__(
            referance=f"{ref_name}",
            amplicon_prefix=f"{amplicon_prefix}_{self.amplicon_number}",
            pool=self.pool + 1,
        )


class BedPrimer:
    ref: str
    _start: int
    _end: int
    primername: str
    pool: int
    direction: str
    sequence: str
    # Calc values
    amplicon_number: int

    def __init__(self, bedline: list[str]) -> None:
        self.ref = bedline[0]
        self._start = int(bedline[1])
        self._end = int(bedline[2])
        self.primername = bedline[3]
        self.pool = int(bedline[4]) - 1
        self.direction = bedline[5]
        self.sequence = bedline[6]

        # Calc some metrics
        result = re_primer_name(self.primername)
        if result is None:
            self.amplicon_number = 0
        else:
            self.amplicon_number = int(result[0])

    def all_seqs(self) -> set[str]:
        "Expands ambs bases"
        return expand_ambs([self.sequence])

    @property
    def msa_index(self) -> str:
        return self.ref

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    def __str__(self, *kwargs) -> str:
        # I use *kwargs so that it can have the same behavor as PrimerPairs
        return f"{self.ref}\t{self.start}\t{self.end}\t{self.primername}\t{self.pool + 1}\t{self.direction}\t{self.sequence}"


class PrimerRecord(abc.ABC):
    @abc.abstractmethod
    def all_seqs(self) -> set[str]:
        pass

    @abc.abstractproperty
    def msa_index(self) -> str | int:
        pass

    @abc.abstractproperty
    def pool(self) -> int:
        pass


class Scheme:
    _pools: list[list[PrimerRecord]]
    _current_pool: int
    npools: int
    _last_pp_added: PrimerRecord
    _matchDB: MatchDB
    cfg: dict

    def __init__(self, cfg, matchDB: MatchDB):
        self.n_pools = cfg["npools"]
        self._pools: list[list[PrimerRecord]] = [[] for _ in range(self.n_pools)]
        self._matches: list[set[tuple]] = [set() for _ in range(self.n_pools)]
        self._current_pool = 0
        self._pp_number = 1
        self.cfg = cfg
        self._matchDB = matchDB

    @property
    def npools(self) -> int:
        return self.n_pools

    def next_pool(self) -> int:
        return (self._current_pool + 1) % self.n_pools

    def add_primer_pair_to_pool(self, primerpair: PrimerPair, pool, msa_index):
        """Main method to add a primerpair to a pool"""
        # Set the primerpair values
        primerpair.pool = pool
        primerpair.msa_index = msa_index
        primerpair.amplicon_number = len(
            [
                pp
                for sublist in self._pools
                for pp in sublist
                if pp.msa_index == msa_index
            ]
        )

        # Adds the primerpair's matches to the pools matches
        self._matches[pool].update(
            primerpair.find_matches(
                self._matchDB,
                fuzzy=self.cfg["mismatch_fuzzy"],
                remove_expected=True,
                kmersize=self.cfg["mismatch_kmersize"],
            )
        )

        # Adds the primerpair to the pool
        self._pools[pool].append(primerpair)
        self._current_pool = pool
        self._current_pool = self.next_pool()
        self._last_pp_added = primerpair

    def add_first_primer_pair(self, primerpairs: list[PrimerPair], msa_index) -> bool:
        "Adds primerpair to the current pool, and updates the current pool"

        # Try and add the first primerpair to an empty pool
        for pool_index in range(self.n_pools):
            if not self._pools[pool_index]:
                self.add_primer_pair_to_pool(primerpairs[0], pool_index, msa_index)
                return True

        # Create a hashmap of what seqs are in each pool for quicklook up
        pool_seqs_map: dict[int : list[str]] = {
            index: [
                y
                for sublist in (x.all_seqs() for x in self._pools[index])
                for y in sublist
            ]
            for index in range(self.n_pools)
        }

        # Adds the first valid primerpair
        for primerpair in primerpairs:
            for pool_index in range(self.n_pools):
                if not do_pools_interact_py(
                    list(primerpair.all_seqs()),
                    pool_seqs_map[pool_index],
                    self.cfg["dimerscore"],
                ) and not detect_new_products(
                    primerpair.find_matches(
                        self._matchDB,
                        remove_expected=False,
                        kmersize=self.cfg["mismatch_kmersize"],
                        fuzzy=self.cfg["mismatch_fuzzy"],
                    ),
                    self._matches[pool_index],
                    self.cfg["mismatch_product_size"],
                ):
                    self.add_primer_pair_to_pool(primerpair, pool_index, msa_index)
                    return True

        # If not primerpair can be added return false
        return False

    def get_seqs_in_pool(self) -> list[str]:
        return [
            y
            for sublist in (x.all_seqs() for x in self._pools[self._current_pool])
            for y in sublist
        ]

    def get_leading_coverage_edge(self) -> tuple[int, int]:
        """This will return the furthest primer-trimmed region with coverage"""
        # This will crash if no primer has been added, but should not be called until one is
        return self._last_pp_added.rprimer.start

    def get_leading_amplicon_edge(self) -> tuple[int, int]:
        """This will return the furthest point of an amplicon"""
        # This will crash if no primer has been added, but should not be called until one is
        return max(self._last_pp_added.rprimer.ends())

    def try_ol_primerpairs(self, all_pp_list, cfg, msa_index) -> bool:
        """
        This will try and add this primerpair into any valid pool.
        Will return true if the primerpair has been added
        """
        last_pool = self._last_pp_added.pool
        # Find what other pools to look in
        pos_pools_indexes = [
            (last_pool + i) % self.n_pools
            for i in range(self.n_pools)
            if (last_pool + i) % self.n_pools != last_pool
        ]

        # Create a hashmap of all sequences in each pool for quick look up
        index_to_seqs: dict[int : list[str]] = {
            index: [
                y
                for sublist in (x.all_seqs() for x in self._pools[index])
                for y in sublist
            ]
            for index in pos_pools_indexes
        }

        # Find pp that could ol, depending on which pool
        pos_ol_pp = [
            pp
            for pp in all_pp_list
            if pp.fprimer.end
            < self.get_leading_coverage_edge() - self.cfg["min_overlap"]
            and pp.rprimer.start
            > self.get_leading_amplicon_edge() + self.cfg["min_overlap"]
        ]

        # pos_ol_pp = get_pp_window(all_pp_list, fp_start=self.get_leading_coverage_edge() - self.cfg["min_overlap"] - self.cfg["amplicon_size_max"], fp_end=self.get_leading_coverage_edge() - self.cfg["min_overlap"], rp_end=self.get_leading_amplicon_edge() + self.cfg["min_overlap"])
        # Sort the primerpairs depending on how good they are
        pos_ol_pp.sort(
            key=lambda pp: ol_pp_score(
                pp.rprimer.start,
                len(pp.all_seqs()),
                self.get_leading_coverage_edge() - self.cfg["min_overlap"],
                self.cfg,
            ),
            reverse=True,
        )

        # For each primerpair
        for ol_pp in pos_ol_pp:
            # For each pool
            for pool_index in pos_pools_indexes:
                # If the pool is empty
                if not self._pools[pool_index]:
                    self.add_primer_pair_to_pool(ol_pp, pool_index, msa_index)
                    return True

                # If the last primer is from the same msa and does clash, skip it
                if self._pools[pool_index][-1].msa_index == msa_index and max(
                    self._pools[pool_index][-1].rprimer.ends()
                ) >= min(ol_pp.fprimer.starts()):
                    continue

                # If the primer passes all the checks, make sure there are no interacts between new pp and pp in pool
                if not do_pools_interact_py(
                    ol_pp.all_seqs(),
                    index_to_seqs.get(pool_index),
                    self.cfg["dimerscore"],
                ) and not detect_new_products(
                    ol_pp.find_matches(
                        self._matchDB,
                        remove_expected=False,
                        kmersize=self.cfg["mismatch_kmersize"],
                        fuzzy=self.cfg["mismatch_fuzzy"],
                    ),
                    self._matches[pool_index],
                    self.cfg["mismatch_product_size"],
                ):
                    self.add_primer_pair_to_pool(ol_pp, pool_index, msa_index)
                    return True

        # If non of the primers work, return false
        return False

    def try_walk_primerpair(self, all_pp_list, cfg, msa_index) -> bool:
        """
        Find the next valid primerpair while walking forwards
        """
        last_pool = self._last_pp_added.pool
        # Find what other pools to look in, can look in same pool
        pos_pools_indexes = [
            (last_pool + i) % self.n_pools for i in range(self.n_pools)
        ]

        # Create a hashmap of all sequences in each pool for quick look up
        index_to_seqs: dict[int : list[str]] = {
            index: [
                y
                for sublist in (x.all_seqs() for x in self._pools[index])
                for y in sublist
            ]
            for index in pos_pools_indexes
        }

        # Find all posiable valid primerpairs
        pos_walk_pp = [
            pp
            for pp in all_pp_list
            if pp.fprimer.end
            > (self.get_leading_coverage_edge() - (self.cfg["min_overlap"] * 2))
        ]
        # Sort walk primers by increasing start position
        pos_walk_pp.sort(
            key=lambda pp: walk_pp_score(
                pp.fprimer.end, len(pp.all_seqs()), self._last_pp_added.end
            )
        )

        # For each primer, try each pool
        for walk_pp in pos_walk_pp:
            for pool_index in pos_pools_indexes:
                # If the pool is empty add the first primer
                if not self._pools[pool_index]:
                    self.add_primer_pair_to_pool(walk_pp, pool_index, msa_index)
                    return True

                # If the last primer is from the same msa and does clash, skip it
                if self._pools[pool_index][-1].msa_index == msa_index and max(
                    self._pools[pool_index][-1].rprimer.ends()
                ) >= min(walk_pp.fprimer.starts()):
                    continue

                # Check if the walking primer clashes with the primer already in the pool
                if not do_pools_interact_py(
                    walk_pp.all_seqs(),
                    index_to_seqs.get(pool_index),
                    self.cfg["dimerscore"],
                ) and not detect_new_products(
                    walk_pp.find_matches(
                        self._matchDB,
                        remove_expected=False,
                        kmersize=self.cfg["mismatch_kmersize"],
                        fuzzy=self.cfg["mismatch_fuzzy"],
                    ),
                    self._matches[pool_index],
                    self.cfg["mismatch_product_size"],
                ):
                    self.add_primer_pair_to_pool(walk_pp, pool_index, msa_index)
                    return True

        return False

    def all_primers(self) -> list[PrimerPair]:
        all_pp = [pp for pool in (x for x in self._pools) for pp in pool]
        all_pp.sort(key=lambda pp: (str(pp.msa_index), pp.amplicon_number))
        return all_pp
