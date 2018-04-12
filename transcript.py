# TALON: Techonology-Agnostic Long Read Analysis Pipeline
# Author: Dana Wyman
#------------------------------------------------------------------------------

class Transcript(object):
    """Stores information about a gene transcript, including its location
       and constitutive exons.

       Attributes:
           chromosome: Chromosome that the transcript is located on 
           (format "chr1")

           start: The start position of the transcript with respect to the
           forward strand 

           end: The end position of the transcript with respect to the
           forward strand

           strand: "+" if the transcript is on the forward strand, and "-" if
           it is on the reverse strand

           exons: List containing start and end position of each exon in sorted
           order

       Optional Attributes:
           gene_id: ID of the gene that this transcript belongs to 

           transcript_id: Accession ID of transcript, i.e. and Ensembl ID

           transcript_name: Human-readable name of the transcript

    """

    def __init__(self, identifier, name, chromosome, \
                 start, end, strand, gene_id):
        self.chromosome = chromosome
        self.start = int(start)
        self.end = int(end)
        self.strand = strand
        self.exons = []

        self.identifier = identifier
        self.name = name
        self.gene_id = gene_id

    def add_exon(self, exon_start, exon_end):
        """Adds an exon (start-end position pair) to the transcript."""

        if exon_start > exon_end:
            raise ValueError('Exon start (' + str(exon_start) + ')' + \
                'is supposed to be before the exon end (' + str(exon_end) + ')')
 
        exon = [exon_start, exon_end]
        self.exons += exon
        return

    def add_exon_from_gtf(self, exon_info):
        """ Adds an exon to the transcript using information from a GTF entry

            Args:
               exon_info: A list containing fields from a GTF file exon entry.
               Example:   
               ['chr1', 'HAVANA', 'exon', '11869', '12227', '.', '+', '.', 
                'gene_id "ENSG00000223972.5"; transcript_id "ENST00000456328.2"; 
                gene_type "transcribed_unprocessed_pseudogene"; 
                gene_status "KNOWN"; gene_name "DDX11L1"; 
                transcript_type "processed_transcript"; 
                transcript_status "KNOWN"; transcript_name "DDX11L1-002"; 
                exon_number 1; exon_id "ENSE00002234944.1"; level 2; 
                tag "basic"; transcript_support_level "1"; 
                havana_gene "OTTHUMG00000000961.2"; 
                havana_transcript "OTTHUMT00000362751.1";'] 
        """
        description = exon_info[-1]
        start = int(exon_info[3])
        end = int(exon_info[4])

        if "transcript_id" not in description:
            raise ValueError('GTF exon entry lacks a transcript_id field')
        transcript_id = (description.split("transcript_id ")[1]).split('"')[1]
        
        if transcript_id != self.identifier:
            raise ValueError('Transcript ID assigned to exon does not match '+ \
                            'transcript it is being assigned to (' + \
                             transcript_id + ' != ' + self.identifier + ')')

        self.add_exon(start, end)
        return

#    def exon_string(self):
#        """ Returns a string representation of the transcript object consisting
#        of its constitutive exon coordinates 
#        """

#        exon_string = ""
#        for exon in self.exons:
#            if exon_string != "":
#                exon_string += "_"
#            exon_string += "-".join([str(x) for x in exon])
#        return exon_string

    def print_transcript(self):
        """ Print a string representation of the Transcript. Good for debugging
        """
        transcript_id = self.identifier
        if transcript_id == None:
            transcript_id = "Transcript"
        if self.name != None:
            # Include name in output if there is one
            print transcript_id + " (" + self.name + "):"
        else:
            print transcript_id + ":"

        print "\tLocation: " + self.chromosome + ":" + str(self.start) + "-" + \
              str(self.end) + "(" + self.strand + ")"

        # Print exons
        print "\tExon: " + "_".join([str(x) for x in self.exons])
        return 

def get_transcript_from_gtf(transcript_info):
    """ Uses information from a GTF-formatted transcript entry to create a
    Transcript object.

        Args:
            transcript_info: A list containing fields from a GTF file gene 
            entry. Example:
          
            chr1	HAVANA	transcript	12010	13670	.	+
            .	gene_id "ENSG00000223972.5"; transcript_id "ENST00000450305.2"; 
            gene_type "transcribed_unprocessed_pseudogene"; 
            gene_status "KNOWN"; gene_name "DDX11L1"; 
            transcript_type "transcribed_unprocessed_pseudogene"; 
            transcript_status "KNOWN"; transcript_name "DDX11L1-001"; 
            level 2; ont "PGO:0000005"; ont "PGO:0000019"; tag "basic"; 
            transcript_support_level "NA"; havana_gene "OTTHUMG00000000961.2"; 
            havana_transcript "OTTHUMT00000002844.2";
    """
    chromosome = transcript_info[0]
    description = transcript_info[-1]
    start = int(transcript_info[3])
    end = int(transcript_info[4])
    strand = transcript_info[6]

    name = None
    gene_id = None
    if "transcript_id" not in description:
            raise ValueError('GTF entry lacks a transcript_id field')
    transcript_id = (description.split("transcript_id ")[1]).split('"')[1]

    if "transcript_name" in description:
        name = (description.split("transcript_name ")[1]).split('"')[1]

    if "gene_id" in description:
        gene_id = (description.split("gene_id ")[1]).split('"')[1]

    transcript = Transcript(transcript_id, name, chromosome, start, end, \
                            strand, gene_id)
    return transcript

