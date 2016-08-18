#!/usr/bin/env python2
""" the main CLI for calling tetrad """

from __future__ import print_function, division  # Requires Python 2.7+

from ipyrad.core.parallel import ipcontroller_init
from ipyrad.assemble.util import IPyradWarningExit
import pkg_resources
import ipyrad as ip
import numpy as np
import argparse
import logging
import sys
import os
import atexit

import ipyrad.analysis as ipa

# pylint: disable=W0212
# pylint: disable=C0301

LOGGER = logging.getLogger(__name__)


def parse_command_line():
    """ Parse CLI args. Only three options now. """

    ## create the parser
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
  * Example command-line usage ---------------------------------------------- 

  * Read in sequence/SNP data file, provide linkage, output name, ambig option. 
     tetrad -s data.snps.phy -n test             ## input phylip and give name
     tetrad -s data.snps.phy -l data.snps.map    ## use one SNP per locus
     tetrad -s data.snps.phy -n noambigs -r 0    ## do not use hetero sites

  * Load saved/checkpointed analysis from '.tet.json' file, or force restart. 
     tetrad -j test.tet.json -b 100         ## continue 'test' until 100 boots
     tetrad -j test.tet.json -b 100 -f      ## force restart of 'test'

  * Sampling modes: 'equal' uses guide tree to sample quartets more efficiently 
     tetrad -s data.snps -m all                         ## sample all quartets
     tetrad -s data.snps -m random -q 1e6 -x 123        ## sample 1M randomly
     tetrad -s data.snps -m equal -q 1e6 -t guide.tre   ## sample 1M across tree

  * HPC optimization: Set -c to the number of nodes to improve efficiency
     tetrad -s data.phy -c 4             ## e.g., use 16 cores across 4 nodes

  * Documentation: http://ipyrad.readthedocs.org/en/latest/
    """)

    ## add arguments 

    ## get version from ipyrad 
    ipyversion = str(pkg_resources.get_distribution('ipyrad'))
    parser.add_argument('-v', '--version', action='version', 
        version="tetrad "+ipyversion.split()[1])

    parser.add_argument('-f', "--force", action='store_true',
        help="force overwrite of existing data")

    #parser.add_argument('-q', "--quiet", action='store_true',
    #    help="do not print to stderror or stdout.")

    parser.add_argument('-s', metavar="seq", dest="seq",
        type=str, default=None,
        help="path to input phylip file (SNPs of full sequence file)")

    parser.add_argument('-j', metavar='json', dest="json",
        type=str, default=None,
        help="load checkpointed/saved analysis from JSON file.")

    parser.add_argument('-m', metavar="method", dest="method",
        type=str, default="all",
        help="method for sampling quartets (all, random, or equal)")

    parser.add_argument('-q', metavar="nquartets", dest="nquartets",
        type=int, default=0,
        help="number of quartets to sample (if not -m all)")

    parser.add_argument('-b', metavar="boots", dest="boots",
        type=int, default=0,
        help="number of non-parametric bootstrap replicates")

    parser.add_argument('-l', metavar="map_file", dest="map",
        type=str, default=None,
        help="map file of snp linkages (e.g., ipyrad .snps.map)")

    parser.add_argument('-r', metavar="resolve", dest='resolve', 
        type=int, default=1, 
        help="randomly resolve heterozygous sites (default=1)")

    parser.add_argument('-n', metavar="name", dest="name",
        type=str, default="test",
        help="output name prefix (default: 'test')")

    parser.add_argument('-o', metavar="outdir", dest="outdir",
        type=str, default="./analysis_tetrad",
        help="output directory (default: creates ./analysis_tetrad)")

    parser.add_argument('-t', metavar="starting_tree", dest="tree",
        type=str, default=None,
        help="newick file starting tree for equal splits sampling")

    parser.add_argument("-c", metavar="compute_nodes", dest="cnodes",
        type=int, default=1,
        help="setting n Nodes improves parallel efficiency on HPC")

    parser.add_argument("-x", metavar="random_seed", dest="rseed",
        type=int, default=None,
        help="random seed for quartet sampling and/or bootstrapping")    

    parser.add_argument('-d', "--debug", action='store_true',
        help="print lots more info to debugger: ipyrad_log.txt.")

    ## if no args then return help message
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    ## parse args
    args = parser.parse_args()

    ## RAISE errors right away for some bad argument combinations:
    if args.method not in ["random", "equal", "all"]:
        raise IPyradWarningExit("  method argument (-m) must be one of"+\
        """ "all", "random", or "equal.\n""")

    ## if 'random' require nquarts argument
    if args.method == 'random':
        if not args.nquartets:
            raise IPyradWarningExit(\
            "  Number of quartets (-q) is required with method = random\n")

    ## if 'equal' method require starting tree and nquarts
    if args.method == 'equal':
        if not args.nquartets:
            raise IPyradWarningExit(\
            "  Number of quartets (-q) is required with method = equal\n")
        if args.tree:
            raise IPyradWarningExit(\
        "  Using a starting tree to equalize edge sampling ")
        #"  A starting tree (-t newick file) is required with method = equal")

    if not any(x in ["seq", "json"] for x in vars(args).keys()):
        print("""
    Bad arguments: tetrad command must include at least one of (-s or -j) 
    """)
        parser.print_help()
        sys.exit(1)

    return args




def main():
    """ main function """
    ## not in ipython
    ip.__interactive__ = 0

    ## parse params file input (returns to stdout if --help or --version)
    args = parse_command_line()

    header = """
 ----------------------------------------------------------------------
  tetrad [v.{}]
  Quartet inference from phylogenetic invariants
  Distributed as part of the ipyrad.analysis toolkit
 ----------------------------------------------------------------------\
  """.format(ip.__version__)
    print(header)

    ## set random seed
    np.random.seed(args.rseed)

    ## debugger----------------------------------------
    if os.path.exists(ip.__debugflag__):
        os.remove(ip.__debugflag__)
    if args.debug:
        print("\n  ** Enabling debug mode ** ")
        ip.debug_on()
        atexit.register(ip.debug_off)      

    ## if JSON, load existing Quartet analysis -----------------------
    if args.json:
        data = ipa.tetrad.load_json(args.json)

        ## if force then remove all results
        if args.force:
            data.refresh()

    ## else create a new tmp assembly for the seqarray-----------------
    else:
        ## create new Quartet class Object if it doesn't exist
        newjson = os.path.join(args.outdir, args.name+'.tet.json')
        if (not os.path.exists(newjson)) or args.force:
            data = ipa.tetrad.Quartet(args.name, args.outdir, args.method)
        else:
            raise IPyradWarningExit("""\
    Error: tetrad analysis '{}' already exists in {} 
    Use the force argument (-f) to overwrite old analysis files, or,
    Use the JSON argument (-j {}/{}.tet.json) 
    to continue analysis of '{}' from last checkpoint.
    """.format(args.name, args.outdir, args.outdir, args.name, args.name))

        ## if input files
        if args.map: 
            data.files.mapfile = args.map
        if args.tree:
            data.files.treefile = args.tree

        ## get seqfile and names from seqfile
        data.files.seqfile = args.seq
        data.resolve_ambigs = args.resolve
        data.init_seqarray()
        data.parse_names()

        ## if quartets not entered then sample all
        if args.nquartets:
            data.nquartets = int(args.nquartets)
        else:
            data.nquartets = ipa.tetrad.n_choose_k(len(data.samples), 4)

        if data.method != 'equal':
            ## store N sampled quartets into the h5 array
            data.store_N_samples()

        else:
            ## infer a starting tree from the N sampled quartets 
            ## this could take a long time. Calls the parallel client.
            raise IPyradWarningExit(\
                "  The 'equal' sampling method is still under development\n")
                #data.store_equal_samples()

    ## boots can be set either for a new object or loaded JSON to continue it
    if args.boots:
        data.nboots = int(args.boots)

    ## This analysis is threaded differently from ipyrad, and thus we want to
    ## set up assuming hyperthreaded cores, user passes nnodes on HPC
    ## Use ipcluster info passed to command-line this time
    data._ipcluster["cores"] = str(args.cnodes)
    if args.cnodes:
        data.cnodes = int(args.cnodes)
        data.cpus = int(ip.assemble.util.detect_cpus())
    #data._ipcluster["engines"] = "MPI"
    data._ipcluster["engines"] = "Local"

    ## launch ipcluster and register for later destruction.
    data = ipcontroller_init(data)

    ## message about whether we are continuing from existing
    if data.checkpoint.boots or data.checkpoint.arr:
        print(ipa.tetrad.LOADING_MESSAGE.format(
              data.method, data.checkpoint.arr, data.checkpoint.boots))

    ## run tetrad main function within a wrapper. The wrapper creates an 
    ## ipyclient view and appends to the list of arguments to run 'run'. 
    data.run(force=args.force)



if __name__ == "__main__": 
    main()

