.. include:: global.rst

.. _assembly_methods:

Assembly Methods
================
ipyrad_ has four methods for assembling RAD-seq data sets. The first and simplest 
is denovo_, which requires no prior information or genomic resources, while the 
remaining three methods all require some form of reference sequence. It is 
important to note, however, that many types of genomic resources can be used as
a reference sequence, not just complete nuclear genomes. For example, 
plastome and transcriptome data can be used to partition reads among 
assemblies with different types of data, and reference sequences can even 
represent the genomes of symbiotic partners, or contaminants to be 
filtered/removed from a data set.

.. _denovo:  
denovo
------
Sequences are assembled without any reference resources. Homology is inferred during
alignment clustering by sequence similarity using the program vsearch_. 

.. _reference:  
reference
---------
Sequences are mapped to a reference genome using the program bwa_ 
(or smalt_, optionally) based on sequence similarity. 

.. _denovo_plus:
denovo+reference
-----------------
Sequences are mapped to a reference genome based on sequence similarity, and 
reads that do not match to the reference are assembled using the denovo method. 

.. _denovo_minus:
denovo-reference
-----------------
Sequences which map to a reference genome are excluded, and all remaining reads
are assembled using the denovo method. This method can be used to filter out 
data, such as reads matching to a chloroplast genome in plants, 
or to a host genome in a study of a parasite. 


.. _comparing:
Combining multiple methods
--------------------------
You could imagine that if you had a reference sequence file you might want to 
examine your data set under a number of different Assembly scenarios. For example,
let's imagine we are interested in inferring phylogeny for a clade of 10 plant
species and we download transcriptome data for a close relative of our focal 
clade. We could assemble our RAD-seq data set using only the data that match
to the transcriptome (putatively coding regions), and compare this with results
when we assemble all of the data that do not match to the transcriptome 
(putatively non-coding). 


Example CLI combining assembly methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    ## create a params.txt file and name it "coding". Then use a text editor
    ## to edit the parameter settings in coding-params.txt and enter the path
    ## to the transcriptome.fasta file for the 'reference_sequence_path', and
    ## enter 'reference' for the 'assembly_method' parameter.
    ipyrad -n coding

    ## run steps 1-2 using the settings in data1-params.txt
    ipyrad -p params-coding.txt -s 12

    ## create a branch called "noncoding" and edit the newly created file 
    ## noncoding-params.txt. Set the assembly_method to 'denovo-reference'
    ## and leave the transcriptome.fasta file as the 'reference_sequence_path'
    ipyrad -p params-coding.txt -b noncoding

    ## now run steps 3-7 for both assemblies
    ipyrad -p params-coding.txt -s 34567
    ipyrad -p params-noncoding.txt -s 34567


Example Python API combining assembly methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    ## import ipyrad 
    import ipyrad as ip

    ## create an Assembly and modify some parameter settings
    data1 = ip.Assembly("coding")
    data1.set_params("project_dir", "example")
    data1.set_params("sorted_fastq_path", "data/*.fastq")
    data1.set_params("reference_sequence_path", "transcriptome.fa")     
    data1.set_params("assembly_method", "reference")

    ## run steps 1-2
    data1.run("12")

    ## create branch named 'noncoding' which inherits params from 'coding'
    ## and set the assembly method to denovo-reference so that it removes the 
    ## reference matched reads.
    data2 = data1.branch("noncoding")
    data2.set_params("assembly_method", "denovo-reference")

    ## finish both assemblies
    data1.run("34567")
    data2.run("34567")

    ## See ipyrad analysis tools for comparing the results.





