import pathlib
from primal_digest.classes import BedPrimer
from itertools import groupby
import sys


def read_bedfile(path: pathlib.Path) -> list[BedPrimer]:
    # Read in the raw primer data
    bed_primers = []
    with open(path, "r") as bedfile:
        for line in bedfile.readlines():
            # If the line is not empty
            if line:
                line = line.strip().split()
                bed_primers.append(BedPrimer(line))
    return bed_primers


def parse_bedfile(bedfile_path: pathlib.Path, npools: int) -> list[list[BedPrimer]]:
    # Read in the raw primer data
    bed_primers = read_bedfile(bedfile_path)
    # Check the number of pools in the given bedfile, is less or equal to npools arg
    pools_in_bed = {primer.pool for primer in bed_primers}
    if len(pools_in_bed) > npools:
        sys.exit(
            f"ERROR: The number of pools in the bedfile is greater than --npools: {len(pools_in_bed)} > {npools}"
        )
    # Asign each bedprimer into the correct pool
    pool = [[] for _ in range(npools)]
    for pool_index, group in groupby(bed_primers, lambda primer: primer.pool):
        pool[pool_index].extend(group)
    return pool
