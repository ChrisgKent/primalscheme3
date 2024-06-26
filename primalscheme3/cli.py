#!/usr/bin/python3
import argparse
import pathlib
from typing import Optional

import typer
from typing_extensions import Annotated

# Module imports
from primalscheme3.__init__ import __version__
from primalscheme3.core.config import Config
from primalscheme3.core.mapping import MappingType
from primalscheme3.core.progress_tracker import ProgressManager
from primalscheme3.interaction.interaction import visulise_interactions
from primalscheme3.panel.panel_main import PanelRunModes, panelcreate
from primalscheme3.remap.remap import remap
from primalscheme3.repair.repair import repair

# Import main functions
from primalscheme3.scheme.scheme_main import schemecreate, schemereplace

## Commands are in the format of
# {pclass}-{mode}
# pclass = pannel or scheme

# Example to create a scheme
# scheme-create

# To repair a scheme
# scheme-repair

# To create a pannel
# pannel-create


def check_path_is_file(value: str | pathlib.Path) -> pathlib.Path:
    if isinstance(value, str):
        value = pathlib.Path(value)
    if not value.is_file():
        raise argparse.ArgumentTypeError(f"No file found at: '{str(value.absolute())}'")
    return value


# Create the main app
app = typer.Typer(name="PrimalScheme3", no_args_is_help=True)


def check_output_dir(output: pathlib.Path, force: bool):
    if output.exists() and not force:
        raise typer.BadParameter(
            f"--output '{output}' directory already exists. Use --force to overwrite"
        )


def typer_callback_version(value: bool):
    if value:
        version = typer.style(__version__, fg=typer.colors.GREEN, bold=True)
        typer.echo("PrimalScheme3 version: " + version)
        raise typer.Exit()


@app.callback()
def primalscheme3(
    value: Annotated[bool, typer.Option] = typer.Option(
        False, "--version", callback=typer_callback_version
    ),
):
    pass


@app.command(no_args_is_help=True)
def scheme_create(
    msa: Annotated[
        list[pathlib.Path],
        typer.Option(
            help="The name of the scheme",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        pathlib.Path,
        typer.Option(
            help="The output directory",
            resolve_path=True,
        ),
    ],
    amplicon_size: Annotated[
        int,
        typer.Option(
            help="The size of an amplicon. Use single value for ± 10 percent [100<=x<=2000]",
        ),
    ] = Config.amplicon_size,
    bedfile: Annotated[
        Optional[pathlib.Path],
        typer.Option(
            help="An existing bedfile to add primers to",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    min_overlap: Annotated[
        int,
        typer.Option(help="min amount of overlap between primers", min=0),
    ] = Config.min_overlap,
    n_pools: Annotated[
        int, typer.Option(help="Number of pools to use", min=1)
    ] = Config.n_pools,
    dimer_score: Annotated[
        float,
        typer.Option(
            help="Threshold for dimer interaction",
        ),
    ] = Config.dimer_score,
    min_base_freq: Annotated[
        float,
        typer.Option(help="Min freq to be included,[0<=x<=1]", min=0.0, max=1.0),
    ] = Config.min_base_freq,
    mapping: Annotated[
        MappingType,
        typer.Option(
            help="How should the primers in the bedfile be mapped",
        ),
    ] = Config.mapping.value,  # type: ignore
    circular: Annotated[
        bool, typer.Option(help="Should a circular amplicon be added")
    ] = Config.circular,
    backtrack: Annotated[
        bool, typer.Option(help="Should the algorithm backtrack")
    ] = Config.backtrack,
    ignore_n: Annotated[
        bool,
        typer.Option(help="Should N in the input genomes be ignored"),
    ] = Config.ignore_n,
    force: Annotated[
        bool, typer.Option(help="Override the output directory")
    ] = Config.force,
    input_bedfile: Annotated[
        Optional[pathlib.Path],
        typer.Option(
            help="Path to a primer.bedfile containing the precalculated primers"
        ),
    ] = Config.input_bedfile,
    high_gc: Annotated[bool, typer.Option(help="Use high GC primers")] = Config.high_gc,
):
    """
    Creates a tiling overlap scheme for each MSA file
    """
    # Update the config with CLI params
    config = Config(**locals())

    # Check the output directory
    check_output_dir(output, force)

    # Set up the progress manager
    pm = ProgressManager()
    schemecreate(msa=msa, output_dir=output, config=config, pm=pm, force=force)


@app.command(no_args_is_help=True)
def scheme_replace(
    primername: Annotated[
        str, typer.Argument(help="The name of the primer to replace")
    ],
    primerbed: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The bedfile containing the primer to replace",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    msa: Annotated[
        pathlib.Path,
        typer.Argument(
            help="The msa used to create the original primer scheme",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    ampliconsize: Annotated[
        int,
        typer.Option(
            help="The size of an amplicon. Use single value for ± 10 percent [100<=x<=2000]",
        ),
    ],
    config: Annotated[
        pathlib.Path,
        typer.Option(
            help="The config.json used to create the original primer scheme",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
):
    """
    Replaces a primerpair in a bedfile
    """
    ampliconsizemin = int(ampliconsize * 0.9)
    ampliconsizemax = int(ampliconsize * 1.1)

    # Set up the progress manager
    pm = ProgressManager()

    schemereplace(
        config_path=config,
        primername=primername,
        ampliconsizemax=ampliconsizemax,
        ampliconsizemin=ampliconsizemin,
        primerbed=primerbed,
        msapath=msa,
        pm=pm,
    )


@app.command(no_args_is_help=True)
def panel_create(
    msa: Annotated[
        list[pathlib.Path],
        typer.Option(
            help="Paths to the MSA files", exists=True, readable=True, resolve_path=True
        ),
    ],
    output: Annotated[
        pathlib.Path,
        typer.Option(
            help="The output directory",
            resolve_path=True,
        ),
    ],
    regionbedfile: Annotated[
        Optional[pathlib.Path],
        typer.Option(help="Path to the bedfile containing the wanted regions"),
    ] = None,
    inputbedfile: Annotated[
        Optional[pathlib.Path],
        typer.Option(
            help="Path to a primer.bedfile containing the precalculated primers"
        ),
    ] = None,
    mode: Annotated[
        PanelRunModes,
        typer.Option(
            help="Select what mode for selecting regions in --regionbedfile",
        ),
    ] = PanelRunModes.REGION_ONLY.value,  # type: ignore
    amplicon_size: Annotated[
        int, typer.Option(help="The size of an amplicon")
    ] = Config.amplicon_size,
    n_pools: Annotated[
        int, typer.Option(help="Number of pools to use", min=1)
    ] = Config.n_pools,
    dimer_score: Annotated[
        float, typer.Option(help="Threshold for dimer interaction")
    ] = Config.dimer_score,
    min_base_freq: Annotated[
        float,
        typer.Option(help="Min freq to be included,[0<=x<=1]", min=0.0, max=1.0),
    ] = Config.min_base_freq,
    mapping: Annotated[
        MappingType,
        typer.Option(
            help="How should the primers in the bedfile be mapped",
        ),
    ] = Config.mapping.value,  # type: ignore
    maxamplicons: Annotated[
        Optional[int], typer.Option(help="Max number of amplicons to create", min=1)
    ] = None,
    force: Annotated[bool, typer.Option(help="Override the output directory")] = False,
    high_gc: Annotated[bool, typer.Option(help="Use high GC primers")] = Config.high_gc,
):
    """
    Creates a primerpanel
    """
    # Update the config with CLI params
    config = Config(**locals())

    # Check the output directory
    check_output_dir(output, force)

    # Set up the progress manager
    pm = ProgressManager()

    panelcreate(
        msa=msa,
        output_dir=output,
        regionbedfile=regionbedfile,
        inputbedfile=inputbedfile,
        mode=mode,
        config=config,
        pm=pm,
        max_amplicons=maxamplicons,
        force=force,
    )


@app.command(no_args_is_help=True)
def interactions(
    bedfile: Annotated[
        pathlib.Path,
        typer.Argument(
            help="Path to the bedfile",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    threshold: Annotated[
        float,
        typer.Option(
            help="Only show interactions more severe (Lower score) than this value",
        ),
    ] = -26.0,
):
    """
    Shows all the primer-primer interactions within a bedfile
    """
    visulise_interactions(bedfile, threshold)


@app.command(no_args_is_help=True)
def repair_mode(
    bedfile: Annotated[
        pathlib.Path,
        typer.Option(
            help="Path to the bedfile",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    msa: Annotated[
        pathlib.Path,
        typer.Option(
            help="An MSA, with the reference.fasta, aligned to any new genomes with mutations",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    config: Annotated[
        pathlib.Path,
        typer.Option(
            help="Path to the config.json",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        pathlib.Path, typer.Option(help="The output directory", dir_okay=True)
    ],
    force: Annotated[bool, typer.Option(help="Override the output directory")] = False,
):
    """
    Repairs a primer scheme via adding more primers to account for new mutations
    """
    # Set up the progress manager
    pm = ProgressManager()

    repair(
        cores=1,
        config_path=config,
        bedfile_path=bedfile,
        force=force,
        pm=pm,
        output_dir=output,
        msa_path=msa,
    )


@app.command(no_args_is_help=True)
def remap_mode(
    bedfile: Annotated[
        pathlib.Path,
        typer.Option(
            help="Path to the bedfile",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    id_to_remap_to: Annotated[
        str, typer.Option(help="The ID of the reference genome to remap to")
    ],
    msa: Annotated[
        pathlib.Path,
        typer.Option(
            help="Path to the MSA file",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    output: Annotated[
        pathlib.Path, typer.Option(help="The output directory", dir_okay=True)
    ],
):
    """
    Remaps a primer scheme to a new reference genome
    """
    remap(
        bedfile_path=bedfile,
        id_to_remap_to=id_to_remap_to,
        msa_path=msa,
        output_dir=output,
    )
