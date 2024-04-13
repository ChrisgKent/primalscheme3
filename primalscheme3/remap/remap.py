# These functions are used to map a primerscheme to a new reference genome

import pathlib
import sys

from Bio import Seq, SeqIO, SeqRecord

from primalscheme3.core.bedfiles import (
    create_amplicon_str,
    create_bedfile_str,
    read_in_bedprimerpairs,
)
from primalscheme3.core.logger import setup_loger


def remap(args):
    bedfile = args.bedfile
    msa_file = args.msa
    id_to_remap_to = args.id_to_remap_to

    OUTPUT_DIR = pathlib.Path(args.output).absolute()  # Keep absolute path
    # See if the output dir already exsits
    if OUTPUT_DIR.is_dir() and not args.force:
        sys.exit(f"ERROR: {OUTPUT_DIR} already exists, please use --force to override")

    # Create the output dir and a work subdir
    pathlib.Path.mkdir(OUTPUT_DIR, exist_ok=True)
    pathlib.Path.mkdir(OUTPUT_DIR / "work", exist_ok=True)

    # Setup logger
    logger = setup_loger(None)

    # Read in the primerpairs
    primer_pairs, _header = read_in_bedprimerpairs(bedfile)

    # Read in the MSA
    msa_dict = SeqIO.index(str(msa_file), "fasta")

    # Check primer's reference genome is in the msa
    chrom_names = set([primer.chrom_name for primer in primer_pairs])
    if len(chrom_names) > 1:
        # TODO spesify the primer chrom name to remap
        logger.error("More than one reference genome in the primer.bed")
        sys.exit(1)
    remap_chrom = next(iter(chrom_names))
    if remap_chrom not in msa_dict:
        logger.error(
            "chromname:<red>{remap_chrom}</> from primer.bed is not in the MSA",
            remap_chrom=remap_chrom,
        )
        sys.exit(1)
    else:
        logger.info(
            "chromname:<green>{remap_chrom}</> from primer.bed is in the MSA",
            remap_chrom=remap_chrom,
        )

    # Check the new reference genome is in the msa
    if id_to_remap_to not in msa_dict:
        logger.error(
            "Remapping ID: <red>{id_to_remap_to}</> not in the MSA",
            id_to_remap_to=id_to_remap_to,
        )
        sys.exit(1)
    else:
        logger.info(
            "Remapping ID: <green>{id_to_remap_to}</> found in the MSA",
            id_to_remap_to=id_to_remap_to,
        )

    # The the primer's reference genome to the MSA index
    primer_to_msa: dict[int, int] = {}
    ref_index = 0
    for msa_index, ref_base in enumerate(msa_dict[remap_chrom]):  # type: ignore
        if ref_base not in {"", "-"}:
            primer_to_msa[ref_index] = msa_index
            ref_index += 1

    # Create a dict that can map MSA indexes to the new reference genome
    msa_to_new_ref: dict[int, int] = {}
    new_index = 0
    for msa_index, ref_base in enumerate(msa_dict[id_to_remap_to]):  # type: ignore
        if ref_base not in {"", "-"}:
            msa_to_new_ref[msa_index] = new_index
            new_index += 1

    # Grab genome length
    msa_length = len(msa_dict.get(id_to_remap_to))  # type: ignore

    for primerpair in primer_pairs:
        # Dict will always have the key
        pp_fp_msa = primer_to_msa[primerpair.fprimer.end]
        pp_fp_newref = msa_to_new_ref.get(pp_fp_msa)  # type: ignore

        if pp_fp_newref is None:
            # Walk to next valid index
            while pp_fp_newref is None and pp_fp_msa < msa_length:
                pp_fp_msa += 1
                pp_fp_newref = msa_to_new_ref.get(pp_fp_msa)
        # Check fixed
        if pp_fp_newref is None:
            print(
                f"Could not find a valid index for {primerpair.amplicon_prefix}_{primerpair.amplicon_number}_RIGHT: {primerpair.fprimer.end}"
            )
            continue

        primerpair.fprimer.end = pp_fp_newref
        primerpair.fprimer._starts = {
            primerpair.fprimer.end - len(x) for x in primerpair.fprimer.seqs
        }

        # Map the reverse primer
        pp_rp_msa = primer_to_msa[primerpair.rprimer.start]
        pp_rp_newref = msa_to_new_ref.get(pp_rp_msa)  # type: ignore

        if pp_rp_newref is None:
            # Walk left to next valid index
            while pp_rp_newref is None and pp_rp_msa > 0:
                pp_rp_msa -= 1
                pp_rp_newref = msa_to_new_ref.get(pp_rp_msa)

        if pp_rp_newref is None:
            print(
                f"Could not find a valid index for {primerpair.amplicon_prefix}_{primerpair.amplicon_number}_LEFT: {primerpair.fprimer.end}"
            )
            continue

        primerpair.rprimer.start = pp_rp_newref
        primerpair.rprimer._ends = {
            primerpair.rprimer.start + len(x) for x in primerpair.rprimer.seqs
        }

        primerpair.chrom_name = id_to_remap_to

    # Write out the outputfiles
    primer_pairs.sort(key=lambda x: (x.chrom_name, x.fprimer.end))
    _header.append(f"# remapped {remap_chrom} -> {id_to_remap_to}")

    # Write the new primer.bed file
    with open(OUTPUT_DIR / "primer.bed", "w") as f:
        f.write(create_bedfile_str(_header, primer_pairs))  # type: ignore

    # Write amplicon bed file
    with open(OUTPUT_DIR / "amplicon.bed", "w") as outfile:
        outfile.write(create_amplicon_str(primer_pairs))  # type: ignore
    with open(OUTPUT_DIR / "primertrim.amplicon.bed", "w") as outfile:
        outfile.write(create_amplicon_str(primer_pairs, trim_primers=True))  # type: ignore

    # Write the new reference genome out
    with open(OUTPUT_DIR / "reference.fasta", "w") as f:
        records = [
            SeqRecord.SeqRecord(
                Seq.Seq(
                    str(msa_dict[id_to_remap_to].seq).strip().replace("-", "").upper(),  # type: ignore
                ),
                id=id_to_remap_to,
                description="",
            )
        ]
        SeqIO.write(
            records,
            f,
            "fasta",
        )
