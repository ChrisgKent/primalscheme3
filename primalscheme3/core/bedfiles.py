import pathlib
from itertools import groupby
import sys
import re

# Module imports
from primalscheme3.core.seq_functions import expand_ambs
from primalscheme3.core.classes import PrimerPair, FKmer, RKmer

REGEX_PATTERN_PRIMERNAME = re.compile("\\d+(_RIGHT|_LEFT|_R|_L)")


def re_primer_name(string) -> list[str] | None:
    """
    Will return (amplicon_number, R/L) or None
    """
    match = REGEX_PATTERN_PRIMERNAME.search(string)
    if match:
        return match.group().split("_")
    return None


class BedPrimerPair(PrimerPair):
    """Class to contain a single primercloud from a bedfile, which contains the extra info parsed from the bedfile"""

    fprimer: FKmer
    rprimer: RKmer
    chromname: str
    ampliconprefix: str
    msa_index: int

    # Calc values
    _primername: str

    def __init__(
        self,
        fprimer: FKmer,
        rprimer: RKmer,
        msa_index: int,
        chromname: str,
        ampliconprefix: str,
        ampliconnumber: int,
        pool: int,
    ) -> None:
        self.fprimer = fprimer
        self.rprimer = rprimer
        self.chromname = chromname
        self.ampliconprefix = ampliconprefix
        self.msa_index = msa_index
        self.amplicon_number = ampliconnumber
        self.pool = pool

        #
        self._primername = f"{self.amplicon_number}_{self.ampliconprefix}"

    def match_primer_stem(self, primernamestem: str) -> bool:
        return self._primername == primernamestem

    def __str__(self, **kargs) -> str:
        # I use **kwargs so that it can have the same behavor as PrimerPairs
        return super().__str__(self.chromname, self.ampliconprefix)


class BedLine:
    """
    Contains a single line from a bedfile
    self.pool is stored as a 0 based index
    """

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

        # Calc values
        self.amplicon_number = int(self.primername.split("_")[1])

    def all_seqs(self) -> set[str] | None:
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


def read_in_bedlines(path: pathlib.Path) -> list[BedLine]:
    """
    Read in bedlines from a file.

    :param path: The path to the bed file.
    :type path: pathlib.Path
    :return: A list of BedLine objects.
    :rtype: list[BedLine]
    """
    bed_primers = []
    with open(path, "r") as bedfile:
        for line in bedfile.readlines():
            if line:
                line = line.strip().split()
                bed_primers.append(BedLine(line))
    return bed_primers


def read_in_bedprimerpairs(path: pathlib.Path) -> list[BedPrimerPair]:
    """
    Read in a bedfile and return a list of BedPrimerPairs, MSA index is set to None as it is not known at this point
    """
    # Read in the bedfile
    primerpairs: list[BedPrimerPair] = []
    with open(path, "r") as primerbedfile:
        # Read in the raw primer data
        bed_lines: list[BedLine] = []
        for line in primerbedfile.readlines():
            line = line.strip().split()
            bed_lines.append(BedLine(line))

    # Group primers by referance
    ref_to_bedlines: dict[str, list[BedLine]] = dict()
    for ref in {bedline.ref for bedline in bed_lines}:
        ref_to_bedlines[ref] = [x for x in bed_lines if x.ref == ref]

    for ref, ref_bed_lines in ref_to_bedlines.items():
        # Group the bedlines by amplicon number
        for ampliconnumber in {
            int(bedline.amplicon_number) for bedline in ref_bed_lines
        }:
            amplicon_prefix = ref_bed_lines[0].primername.split("_")[0]
            ampliconlines = [
                x for x in ref_bed_lines if x.amplicon_number == ampliconnumber
            ]
            pool = ampliconlines[0].pool
            # Group the ampliconlines by direction
            fkmer = FKmer(
                [x.end for x in ampliconlines if x.direction == "+"][0],
                {x.sequence for x in ampliconlines if x.direction == "+"},
            )
            rkmer = RKmer(
                [x.start for x in ampliconlines if x.direction == "-"][0],
                {x.sequence for x in ampliconlines if x.direction == "-"},
            )
            primerpairs.append(
                BedPrimerPair(
                    fprimer=fkmer,
                    rprimer=rkmer,
                    msa_index=None,  # This is set later # type: ignore
                    chromname=ref,
                    ampliconnumber=int(ampliconnumber),
                    ampliconprefix=amplicon_prefix,
                    pool=pool,
                )
            )

    primerpairs.sort(key=lambda x: (x.chromname, x.amplicon_number))
    return primerpairs
