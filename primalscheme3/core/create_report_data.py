import gzip
import json
import pathlib
from itertools import groupby
from operator import itemgetter

import numpy as np

from primalscheme3.core.classes import PrimerPair

# Module imports
from primalscheme3.core.msa import MSA
from primalscheme3.core.seq_functions import entropy_score_array

# Panel imports
from primalscheme3.panel.minimal_scheme_classes import PanelMSA

# Plot format
# plot1: scheme coverage plot. Can be parsed from the bedfile
# plot2 Base occupancy + genome gc
# plot3: Entropy plot
# plot4: Thermo pass Fkmer and Rkmer plot


def calc_occupancy(align_array: np.ndarray) -> list[tuple[int, float]]:
    results = []
    # Calculate the base proportions
    for index, column in enumerate(align_array.T):
        gaps = np.count_nonzero(column == "-")
        gaps += np.count_nonzero(column == "")
        results.append((index, 1 - (gaps / len(column))))
    return reduce_data(results)


def calc_gc(align_array: np.ndarray, kmer_size: int = 30) -> list[tuple[int, float]]:
    results = []
    # Calculate the base proportions
    for col_index in range(0, align_array.shape[1] - kmer_size, 15):
        slice = align_array[:, col_index : col_index + kmer_size]
        ng = np.count_nonzero(slice == "G")
        nc = np.count_nonzero(slice == "C")

        n_invalid = np.count_nonzero(slice == "-")
        gc_prop = round((ng + nc) / ((len(slice) * kmer_size) - n_invalid), 2)

        results.append((col_index, gc_prop))
    return reduce_data(results)


def reduce_data(results: list[tuple[int, float]]) -> list[tuple[int, float]]:
    """
    Reduce the size of data by merging consecutive points, and rounding to 4 decimal places
    """
    reduced_results = []
    for iindex, (index, oc) in enumerate(results):
        # Add first point
        if iindex == 0:
            reduced_results.append((index, round(oc, 4)))
            continue
        # Add the last point
        if iindex == len(results) - 1:
            reduced_results.append((index, round(oc, 4)))
            continue

        # If the previous point is the same, and the next point is the same
        if results[iindex - 1][1] == oc and results[iindex + 1][1] == oc:
            continue
        else:
            reduced_results.append((index, round(oc, 4)))
    return reduced_results


def generate_uncovered_data(length, primerpairs: list[PrimerPair]) -> dict[int, int]:
    # Set all indexes to uncovered
    uncovered_indexes = {x for x in range(0, length)}

    for primerpair in primerpairs:
        # Handle circular primerpairs
        if primerpair.fprimer.end > primerpair.rprimer.start:
            uncovered_indexes -= set(range(primerpair.fprimer.end, length))
            uncovered_indexes -= set(range(0, primerpair.rprimer.start))
        # Handle linear primerpairs
        else:
            uncovered_indexes -= set(
                range(primerpair.fprimer.end, primerpair.rprimer.start)
            )

    # Plot the uncovered regions
    uncovered_indexes_list = sorted(uncovered_indexes)
    # Generate continous regions
    uncovered_regions = []
    for k, g in groupby(enumerate(uncovered_indexes_list), lambda ix: ix[0] - ix[1]):
        uncovered_regions.append(list(map(itemgetter(1), g)))

    data: dict[int, int] = dict()
    uncovered_regions = [(min(x), max(x)) for x in uncovered_regions]

    for start, end in uncovered_regions:
        data[start] = end
    return data


def generate_genome_gc_data(msa: MSA | PanelMSA, kmersize: int) -> dict[int, float]:
    """Creates a dict of the genome GC% with key as position and value as GC%"""
    gc_data = dict()
    for index, gc in calc_gc(msa.array, kmersize):
        gc_data[index] = gc
    return gc_data


def generate_genome_occupancy_data(msa: MSA | PanelMSA) -> dict[int, float]:
    """Creates a dict of the genome occupancy with key as position and value as occupancy"""
    occupancy_data = dict()
    for x, y in calc_occupancy(msa.array):
        occupancy_data[x] = y
    return occupancy_data


def generate_genome_entropy_data(msa: MSA | PanelMSA) -> dict[int, float]:
    """Creates a dict of the genome entropy with key as position and value as entropy"""
    results = []
    entropy_data = dict()

    try:
        entropy_array = list(msa._entropy_array)  # type: ignore
    except AttributeError:
        entropy_array = entropy_score_array(msa.array)

    # Calculate the entropy score for each position
    for x, y in enumerate(entropy_array):
        results.append((x, y))
    # Reduce the data
    reduced_data = reduce_data(results)
    for x, y in reduced_data:
        entropy_data[x] = y
    return entropy_data


def generate_thermo_pass_primer_data(msa: MSA | PanelMSA) -> dict[int, str]:
    primer_data = dict()

    fprimer_data = dict()
    for fkmer in msa.fkmers:
        fprimer_data[fkmer.end] = len(fkmer.seqs)
    primer_data["F"] = fprimer_data
    rprimer_data = dict()
    for rkmer in msa.rkmers:
        rprimer_data[rkmer.start] = len(rkmer.seqs)
    primer_data["R"] = rprimer_data
    return primer_data


def generate_amplicon_data(
    primerpairs: list[PrimerPair],
) -> dict[str, dict[str, int | str]]:
    """
    Creates the amplicon plot data
    :param primerpairs: list of PrimerPair objects
    :return: dict of amplicon data
    """
    amplicon_data = dict()

    for primerpair in primerpairs:
        amplicon_data[primerpair.amplicon_number] = {
            "s": min(primerpair.fprimer.starts()),
            "cs": primerpair.fprimer.end,
            "ce": primerpair.rprimer.start,
            "e": max(primerpair.rprimer.ends()),
            "p": primerpair.pool + 1,
            "n": f"{primerpair.amplicon_prefix}_{primerpair.amplicon_number}",
        }

    return amplicon_data


def generate_data(msa: MSA | PanelMSA, last_pp_added: list[PrimerPair]) -> dict:
    """
    Generate all the plot data for a single MSA
    :param msa: MSA object
    :param pools: The pools object
    :return: dict of all the plot data
    """
    # Filter the last primerpair added to the multiplex
    msa_pp: list[PrimerPair] = [
        x for x in last_pp_added if x.msa_index == msa.msa_index
    ]

    # Remap the included primers to the MSA if they have been mapped to an genome
    if msa._mapping_array is not None:
        # Create a remapping dict
        remapping_dict = {
            x: i for i, x in enumerate(list(msa._mapping_array)) if x is not None
        }
        for fkmer in msa.fkmers:
            fkmer.end = remapping_dict[fkmer.end]
            fkmer._starts = {fkmer.end - len(x) for x in fkmer.seqs}
        for rkmer in msa.rkmers:
            rkmer.start = remapping_dict[rkmer.start]
            rkmer._ends = {rkmer.start + len(x) for x in rkmer.seqs}

    # Write all data to a single json file
    data = dict()
    data["gc"] = generate_genome_gc_data(msa, 30)
    data["entropy"] = generate_genome_entropy_data(msa)
    data["occupancy"] = generate_genome_occupancy_data(msa)
    data["thermo_pass"] = generate_thermo_pass_primer_data(msa)
    data["amplicons"] = generate_amplicon_data(msa_pp)
    data["dims"] = [x for x in msa.array.shape]
    data["uncovered"] = generate_uncovered_data(msa.array.shape[1], msa_pp)

    return data


def generate_all_plotdata(
    msas: list[MSA] | list[PanelMSA],
    output_path: pathlib.Path,
    last_pp_added: list[PrimerPair],
) -> dict:
    """
    Generate all the plot data for all MSAs to plotdata.json.gz
    :param msa: list of MSA objects
    :param last_pp_added: list of PrimerPair objects added to the multiplex
    :param output_path: pathlib.Path to write the plotdata.json to
    :return: None
    """
    # Write all data to a single json file
    data = dict()
    for msa in msas:
        data[msa._chrom_name] = generate_data(msa, last_pp_added)

    # Write the data to a json file
    json_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
    with gzip.open(output_path / "plotdata.json.gz", "wb") as fout:
        fout.write(json_bytes)

    # Return the data for use in plotting
    return data
