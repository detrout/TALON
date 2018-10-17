# TALON: Techonology-Agnostic Long Read Analysis Pipeline
# Author: Dana Wyman
# -----------------------------------------------------------------------------
# This program reads in a GTF-formatted transcript annotation (ie GENCODE) and
# creates a SQLite database with gene, transcript, and edge tables.
# This database is used by the TALON pipeline to maintain a registry of 
# known annotations as well as novel discoveries.

import sqlite3
from sqlite3 import Error
from optparse import OptionParser
import gene as Gene
import transcript as Transcript
import edge as Edge
import warnings
import os
import time

def getOptions():
    parser = OptionParser()
    parser.add_option("--f", dest = "gtf",
        help = "GTF annotation containing genes, transcripts, and edges.",
        metavar = "FILE", type = "string")
    parser.add_option("--a", dest = "annot_name",
        help = "Name of supplied annotation (will be used to label data)",
        type = "string")
    parser.add_option("--g", dest = "genome_build",
        help = "Name of genome build that the GTF file is based on (ie hg38)",
        type = "string")
    parser.add_option("--l", dest = "min_length",
        help = "Minimum required transcript length (default = 300 bp) ",
        type = "int", default = 300)
    parser.add_option("--o", dest = "outprefix",
        help = "Outprefix for the annotation files",
        metavar = "FILE", type = "string")

    (options, args) = parser.parse_args()
    return options

############### Database initialization section #############################

def create_database(path):
    """ Creates an SQLite database with the provided name. If a database
        of the name already exists, an error is generated. """

    if os.path.isfile(path):
        raise ValueError("Database with name '" + path + "' already exists!")

    try:
        conn = sqlite3.connect(path)
    except Error as e:
        print(e)
    finally:
        conn.commit()
        conn.close()

    return

def add_gene_table(database):
    """ Add a table to the database to track genes. Attributes are:
        - Primary Key: Gene ID (interally assigned by database)
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set primary key column, which will be the gene ID
    c.execute('CREATE TABLE "genes" ("gene_ID" INTEGER PRIMARY KEY)')

    conn.commit()
    conn.close()
    return

def add_transcript_table(database):
    """ Add a table to the database to track transcripts. Attributes are:
        - Primary Key: Transcript ID (interally assigned by database)
        - Gene ID
        - Path (Edges)
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set keys
    command = """ CREATE TABLE IF NOT EXISTS transcripts (
                transcript_ID INTEGER PRIMARY KEY,
                gene_ID INTEGER,
                path TEXT,
                 
                FOREIGN KEY (gene_ID) REFERENCES genes(gene_ID)
                ); """

    c.execute(command)
    conn.commit()
    conn.close()
    return

def add_edge_table(database):
    """ Add a table to the database to track edges linking vertices. 
        Attributes are:
        - Primary Key: ID (interally assigned by database)
        - Donor ID
        - Acceptor ID
    """
    
    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Create edge type table first. 
    add_edgetype_table(database)

    # Add edge table and set keys
    command = """ CREATE TABLE IF NOT EXISTS edge (
                edge_ID INTEGER,
                v1 INTEGER,
                v2 INTEGER,
                edge_type TEXT,
                
                PRIMARY KEY (edge_ID),
                FOREIGN KEY (v1) REFERENCES vertex(ID),
                FOREIGN KEY (v2) REFERENCES vertex(ID),
                FOREIGN KEY (edge_type) REFERENCES edge_type(type)
                ); """

    c.execute(command)
    conn.commit()
    conn.close()
    return

def add_edgetype_table(database):
    """ Add a table to the database to track permitted edge types. We start
        with "edge" and "intron"
        Attributes are:
        - Primary Key: Type
    """
    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set primary key column, which will be the transcript ID
    # Also include relationship to the gene table
    command = """CREATE TABLE IF NOT EXISTS edge_type (type TEXT PRIMARY KEY);"""
    c.execute(command)

    # Add entries for 'exon' and 'intron'
    for t in ["exon", "intron"]:
        cols = "(type)"
        vals = [ t ]
        command = 'INSERT OR IGNORE INTO "edge_type"' + cols + "VALUES " + \
                  '(?)'
        c.execute(command,vals)

    conn.commit()
    conn.close()
    return

#def add_vertextype_table(database):
#    """ Add a table to the database to track permitted vertex types. We start
#        with "start", "end", "donor", and "acceptor"
#        Attributes are:
#        - Primary Key: Type
#    """
#    # Connecting to the database file
#    conn = sqlite3.connect(database)
#    c = conn.cursor()

#    # Add table and set primary key column, which will be the transcript ID
#    # Also include relationship to the gene table
#    command = """CREATE TABLE IF NOT EXISTS vertex_type (type TEXT PRIMARY KEY);"""
#    c.execute(command)

#    # Add entries
#    for t in ["start", "end", "donor", "acceptor"]:
#        cols = "(type)"
#        vals = [ t ]
#        command = 'INSERT OR IGNORE INTO "vertex_type"' + cols + "VALUES " + \
#                  '(?)'
#        c.execute(command,vals)

#    conn.commit()
#    conn.close()
#    return

def add_vertex_table(database):
    """ Add a table to the database to track vertices.
        Attributes are:
        - Primary Key: ID (interally assigned by database)
        - Gene ID
        - Type
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Create vertex type table first.
    #add_vertextype_table(database)

    # Add table and set primary key column, which will be the transcript ID
    # Also include relationship to the gene table
    command = """ CREATE TABLE IF NOT EXISTS vertex (
                vertex_ID INTEGER PRIMARY KEY,
                gene_ID INTEGER,
                
                FOREIGN KEY (gene_ID) REFERENCES genes(gene_ID)
                ); """

    c.execute(command)
    conn.commit()
    conn.close()
    return

def add_genome_table(database, build):
    """ Add a table that tracks the genome builds in use, then add the provided
        genome build to it.
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set primary key column, which will be the edge ID
    c.execute("""CREATE TABLE genome_build (
                     build_ID INTEGER PRIMARY KEY,
                     name TEXT)""")

    # Get value of genome_build counter
    c.execute('SELECT "count" FROM "counters" WHERE "category" = "genome_build"')
    counter = int(c.fetchone()[0])
    db_id = counter + 1
    counter += 1

    # Add entry for current genome build
    cols = "(build_ID, name)"
    vals = [ db_id, build ]
    command = 'INSERT OR IGNORE INTO "genome_build"' + cols + "VALUES " + \
              '(?,?)'
    c.execute(command,vals)

    # Update the counter
    update_counter = 'UPDATE "counters" SET "count" = ? WHERE "category" = ?'
    c.execute(update_counter, [counter, "genome_build"])

    conn.commit()
    conn.close()
    return

def add_dataset_table(database):
    """ Add a table that tracks the datasets added to the database.
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set primary key column
    c.execute("""CREATE TABLE dataset (
                     dataset_ID INTEGER PRIMARY KEY,
                     dataset_name TEXT,
                     sample TEXT,
                     platform TEXT
              )""")

    conn.commit()
    conn.close()
    return

def add_observed_start_table(database):
    """ Add a table that tracks how far observed 5' ends deviate from the
        'official' transcript start.
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set primary key column
    c.execute("""CREATE TABLE observed_transcript_start (
                     obs_start_ID INTEGER PRIMARY KEY,
                     transcript_ID INTEGER,
                     vertex_ID INTEGER,
                     dataset INTEGER,
                     delta INTEGER,

                     FOREIGN KEY(transcript_ID) REFERENCES transcripts(transcript_ID),
                     FOREIGN KEY(dataset) REFERENCES dataset(dataset_ID),
                     FOREIGN KEY(vertex_ID) REFERENCES vertex(vertex_ID)
              )""")

    conn.commit()
    conn.close()
    return

def add_observed_end_table(database):
    """ Add a table that tracks how far observed 5' ends deviate from the
        'official' transcript start.
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set primary key column
    c.execute("""CREATE TABLE observed_transcript_end (
                     obs_end_ID INTEGER PRIMARY KEY,
                     transcript_ID INTEGER,
                     vertex_ID INTEGER,
                     dataset INTEGER,
                     delta INTEGER,

                     FOREIGN KEY(transcript_ID) REFERENCES transcripts(transcript_ID),
                     FOREIGN KEY(dataset) REFERENCES dataset(ID),
                     FOREIGN KEY(vertex_ID) REFERENCES vertex(vertex_ID)
              )""")

    conn.commit()
    conn.close()
    return

def add_abundance_table(database):
    """ Add a table to the database to track transcript abundance over
        all datasets.
        - Transcript ID 
        - Dataset
        - Count
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set primary key column, which will be the edge ID
    c.execute("""CREATE TABLE abundance (
                     transcript_ID INTEGER,
                     dataset INTEGER,
                     count INTEGER,
                     
                 PRIMARY KEY(transcript_ID, dataset),
                 FOREIGN KEY(transcript_ID) REFERENCES transcripts(transcript_ID),
                 FOREIGN KEY(dataset) REFERENCES dataset(dataset_ID)    
              )""")

    conn.commit()
    conn.close()
    return

def add_counter_table(database):
    """ Add a table to the database to track novel events. Attributes are:
        - Category (gene, transcript, edge)
        - Count (number of items in that category so far)
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table and set primary key column
    table_name = "counters"
    c.execute('CREATE TABLE "counters" ("category" TEXT PRIMARY KEY)')

    # Add novel column
    default_val = 0
    c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct}"\
        .format(tn=table_name, cn="count", ct="INTEGER", df=default_val))

    # Add rows
    c.execute("INSERT INTO {tn} ({idf}, {cn}) VALUES ('genes', 0)".\
        format(tn=table_name, idf="category", cn="count"))
    c.execute("INSERT INTO {tn} ({idf}, {cn}) VALUES ('transcripts', 0)".\
        format(tn=table_name, idf="category", cn="count"))
    c.execute("INSERT INTO {tn} ({idf}, {cn}) VALUES ('vertex', 0)".\
        format(tn=table_name, idf="category", cn="count"))
    c.execute("INSERT INTO {tn} ({idf}, {cn}) VALUES ('edge', 0)".\
        format(tn=table_name, idf="category", cn="count"))
    c.execute("INSERT INTO {tn} ({idf}, {cn}) VALUES ('genome_build', 0)".\
        format(tn=table_name, idf="category", cn="count"))
    c.execute("INSERT INTO {tn} ({idf}, {cn}) VALUES ('dataset', 0)".\
        format(tn=table_name, idf="category", cn="count"))
    c.execute("INSERT INTO {tn} ({idf}, {cn}) VALUES ('observed_transcript_start', 0)".\
        format(tn=table_name, idf="category", cn="count"))
    c.execute("INSERT INTO {tn} ({idf}, {cn}) VALUES ('observed_transcript_end', 0)".\
        format(tn=table_name, idf="category", cn="count"))

    conn.commit()
    conn.close()
    return

def add_annotation_table(database, table_name, key_table, fk_id):
    """ Add a table to keep track of annotation attributes for genes,
        transcripts, etc. The table will be given the provided table name. A
        foreign key will be created to link the ID column of the annotation
        table to the fk_id column of the key_table.

        Attributes:
        - Item ID
        - Annotation name: user-provided name for annotation
        - Source (in case of an object from a GTF, this comes from the 2nd col)
        - Feature type
        - Attribute
        - Value
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table
    fk_statement = "FOREIGN KEY (ID) REFERENCES "+ key_table + "(" + fk_id + ")"
    command = " CREATE TABLE IF NOT EXISTS " + table_name + \
                """ (ID INTEGER,
                  annot_name text,
                  source text,
                  attribute text,
                  value text, 
                  PRIMARY KEY (ID, source, attribute), """ + fk_statement + """); """
    c.execute(command)
    conn.commit()
    conn.close()
    return

def add_location_table(database):
    """ Add a table to the database to track the locations of objects across
        the different genome builds. Attributes are:
        - Vertex ID
        - Genome build
        - Chromosome
        - Position (1-based)
        - Strand
    """

    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    # Add table
    command = """ CREATE TABLE IF NOT EXISTS location (
                  location_ID INTEGER,
                  genome_build INTEGER,
                  chromosome text,
                  position INTEGER,
                  strand TEXT,

                  PRIMARY KEY(location_ID, genome_build),
                  FOREIGN KEY(genome_build) REFERENCES genome_build(build_ID),
                  FOREIGN KEY(location_ID) REFERENCES vertex(vertex_ID)
                  ); """
    c.execute(command)

    conn.commit()
    conn.close()
    return


####################### GTF parsing section #################################

def read_gtf_file(gtf_file):
    """ Reads gene, transcript, and edge information from a GTF file.
        Args:
            gtf_file: Path to the GTF file
        Returns:
            genes: A dictionary mapping gene IDs to corresponding gene objects
            transcripts: A dictionary mapping gene IDs to corresponding 
                   transcript objects
            exons: A dictionary mapping exon IDs to corresponding edge objects
    """
    genes = {}
    transcripts = {}
    exons = {}

    with open(gtf_file) as gtf:
        for line in gtf:
            line = line.strip()

            # Ignore header
            if line.startswith("#"):
                continue

            # Split into constitutive fields on tab
            tab_fields = line.split("\t")
            chrom = tab_fields[0]
            entry_type = tab_fields[2]

            # Entry is a gene
            if entry_type == "gene":
                gene = Gene.get_gene_from_gtf(tab_fields)
                native_id = gene.identifier
                genes[native_id] = gene

            # Entry is a transcript
            elif entry_type == "transcript":
                transcript = Transcript.get_transcript_from_gtf(tab_fields)
                gene_id = transcript.gene_id
                if gene_id in genes:
                    genes[gene_id].add_transcript(transcript)
                native_id = transcript.identifier
                transcripts[native_id] = transcript
                
            # Entry is an edge
            elif entry_type == "exon":
                exon = Edge.create_edge_from_gtf(tab_fields)
                # This ID is used because of a rare GENCODE bug
                location_exon_id = exon.identifier
                exons[location_exon_id] = exon 

                transcript_id = list(exon.transcript_ids)[0]
                gene_id = exon.annotations["gene_id"]
                
                if location_exon_id not in exons:
                    # Add the new edge to the data structure
                    exons[location_exon_id] = exon
                else:
                    # Update existing exon entry, including its transcript set
                    exon = exons[location_exon_id]
                    exon.transcript_ids.add(transcript_id)
           
                if transcript_id in transcripts:         
                    currTranscript = transcripts[transcript_id]
                    currTranscript.add_exon(exon)

    return genes, transcripts, exons

def filter_by_length(genes, transcripts, min_length):
    """ Given a minimum transcript length, this function
          - Iterates over transcripts and keeps the ones with length >= min_length
          - Removes genes not represented in the transcript set
    """
    filtered_transcripts = {}
    filtered_genes = {}

    for transcript_id in transcripts:
        curr_transcript = transcripts[transcript_id]
        length = curr_transcript.get_length()

        if length >= min_length:
            filtered_transcripts[transcript_id] = curr_transcript
            gene_id = curr_transcript.gene_id
            if gene_id in genes:
                filtered_genes[gene_id] = genes[gene_id]

    return filtered_genes, filtered_transcripts

def organize_by_chromosome(genes, transcripts):
    """ Iterate through genes and transcripts and group them by chromosome """
    gene_dict = {}
    transcript_dict = {}

    for ID in genes:
        gene = genes[ID]
        chromosome = gene.chromosome
        if chromosome not in gene_dict:
            chrom_genes = {}
            chrom_genes[ID] = gene
            gene_dict[chromosome] = chrom_genes
        gene_dict[chromosome][ID] = gene

    for ID in transcripts:
        transcript = transcripts[ID]
        chromosome = transcript.chromosome
        if chromosome not in transcript_dict:
            chrom_transcripts = {}
            chrom_transcripts[ID] = transcript
            transcript_dict[chromosome] = chrom_transcripts
            transcript_dict[chromosome][ID] = transcript
        transcript_dict[chromosome][ID] = transcript

    return gene_dict, transcript_dict

######################### Populate the database ############################

def populate_db(database, annot_name, chrom_genes, chrom_transcripts, edges, genome_build):
    """ Iterate over GTF-derived gene, transcript, and edge entries in order
        to add a record for each in the database.
    """
    # Connecting to the database file
    conn = sqlite3.connect(database)
    c = conn.cursor()

    for chromosome in chrom_genes.keys():
        start_time = time.time()
        print chromosome
        genes = chrom_genes[chromosome]
        transcripts = chrom_transcripts[chromosome]        

        gene_id_map = add_genes(c, genes, annot_name)
        add_transcripts(c, transcripts, annot_name, gene_id_map, genome_build)

        conn.commit()
        end_time = time.time()
        print "It took {} to process chromosome".format(hms_string(end_time - start_time))
    conn.close()
    
    return

def add_genes(c, genes, annot_name):

    bulk_genes = []
    bulk_annotations = []
    gene_id_map = {}

    # Fetch value of gene counter
    c.execute('SELECT "count" FROM "counters" WHERE "category" = "genes"')
    gene_counter = int(c.fetchone()[0])

    for gene_id in genes:
        gene = genes[gene_id]
        db_gene_id = gene_counter + 1
        gene_counter += 1

        # Information for gene table
        bulk_genes.append((db_gene_id,))

        # Information for gene annotations
        attributes = gene.annotations
        native_gene_id = gene.identifier
        gene_id_map[native_gene_id] = db_gene_id
        source = attributes["source"]

        for att in attributes.keys():
            value = attributes[att]
            bulk_annotations.append((db_gene_id, annot_name, source, att, value))


    print "bulk update genes..."
    bulk_update_genes(c, bulk_genes, gene_counter)
    print "bulk update gene_annotations..."
    bulk_update_gene_annotations(c, bulk_annotations)
    return gene_id_map
 
def bulk_update_genes(c, genes, gene_counter):
    """
       Given a list of tuple-formatted gene entries, this function inserts them
       into the database at the provided cursor (c).
    """
    # Insert entries into database in bulk
    cols = " (" + ", ".join([str_wrap_double(x) for x in ["gene_id"]]) + ") "
    g_command = 'INSERT INTO "genes"' + cols + "VALUES " + '(?)'
    c.executemany(g_command, genes)

    # Update counter
    update_counter = 'UPDATE "counters" SET "count" = ? WHERE "category" = ?'
    c.execute(update_counter, [gene_counter, "genes"])

    return

def bulk_update_gene_annotations(c, bulk_annotations):
    """
       Given a list of tuple-formatted gene annotation entries, this function 
       inserts them into the database at the provided cursor (c).
    """

    cols = " (" + ", ".join([str_wrap_double(x) for x in ["ID","annot_name",
               "source", "attribute", "value"]]) + ") "
    command = 'INSERT INTO "gene_annotations"' + cols + "VALUES " + \
                  '(?,?,?,?,?)'
    c.executemany(command, bulk_annotations)

    return 

def add_transcripts(c, transcripts, annot_name, gene_id_map, genome_build):

    bulk_transcripts = []
    bulk_annotations = []

    # Keep track of vertices and edges as they are created
    vertices = {}
    edges = {}

    # Get vertex and edge counters from database
    c.execute('SELECT "count" FROM "counters" WHERE "category" = "vertex"')
    v_counter = int(c.fetchone()[0])
    vertices['counter'] = v_counter

    c.execute('SELECT "count" FROM "counters" WHERE "category" = "edge"')
    e_counter = int(c.fetchone()[0])
    edges['counter'] = e_counter

    # Get transcript counter
    c.execute('SELECT "count" FROM "counters" WHERE "category" = "transcripts"')
    counter = int(c.fetchone()[0])

    for transcript_id in transcripts:
        # Create transcript entry
        transcript = transcripts[transcript_id]
        db_transcript_id = counter + 1
        counter += 1

        # Extract annotation items and find database-issued gene ID if possible
        attributes = transcript.annotations
        source = attributes["source"]
        native_gene_id = attributes["gene_id"]

        if native_gene_id != "NULL" and native_gene_id != None:
            db_gene_id = gene_id_map[native_gene_id]
        else:
            db_gene_id = "NULL"

        # Process exons to create vertices and edges 
        #start_time = time.time()
        transcript_path, vertices, edges = process_transcript(c,
                                           transcript, db_gene_id, genome_build,
                                           annot_name, vertices, edges)
        bulk_transcripts.append((db_transcript_id, db_gene_id, transcript_path))

        # Create annotation entries
        ignore = ["gene_id", "gene_name"]
        for att in attributes.keys():
            if att in ignore or "gene" in att:
                continue
            value = attributes[att]
            bulk_annotations.append((db_transcript_id, annot_name, source, att, value))
           
    print "bulk update transcripts..."
    bulk_update_transcripts(c, bulk_transcripts, counter)
    print "bulk update annotations..."
    bulk_update_transcript_annotations(c, bulk_annotations)
    print "bulk update vertices/locations..."
    bulk_update_vertices(c, vertices)
    print "bulk update edges..."
    bulk_update_edges(c, edges)

    return

def bulk_update_transcripts(c, transcripts, counter):
    """
       Given a list of tuple-formatted transcript entries, this function inserts them
       into the database at the provided cursor (c).
    """
    cols = " (" + ", ".join([str_wrap_double(x) for x in ["transcript_ID",
           "gene_ID", "path"]]) + ") "
    g_command = 'INSERT INTO "transcripts"' + cols + "VALUES " + \
                '(?,?,?)'
    c.executemany(g_command,transcripts)
 
    update_counter = 'UPDATE "counters" SET "count" = ? WHERE "category" = ?'
    c.execute(update_counter, [counter, "transcripts"])

    return

def bulk_update_transcript_annotations(c, bulk_annotations):
    """
       Given a list of tuple-formatted transcript annotation entries, this 
       function inserts them into the database at the provided cursor (c).
    """
    cols = " (" + ", ".join([str_wrap_double(x) for x in ["ID","annot_name",
                   "source", "attribute", "value"]]) + ") "
    command = 'INSERT INTO "transcript_annotations"' + cols + "VALUES " + \
                  '(?,?,?,?,?)'
    c.executemany(command, bulk_annotations)

    return

def bulk_update_vertices(c, vertices):
    """
       Given a list of tuple-formatted vertex entries, this
       function inserts them into the database at the provided cursor (c).
    """
    # Extract the counter
    counter = vertices.pop("counter")

    # Separate vertex entries and locations
    vertex_list = [ (x[0],x[1]) for x in vertices.values()]
    location_list = [ (x[0],x[2],x[3],x[4],x[5]) for x in vertices.values()]
 
    # Bulk entry of vertices
    cols = " (" + ", ".join([str_wrap_double(x) for x in ["vertex_ID","gene_id"]]) + ") "
    command = 'INSERT INTO "vertex"' + cols + "VALUES " + \
                  '(?,?)'
    c.executemany(command, vertex_list)

    # Bulk entry of locations
    cols = " (" + ", ".join([str_wrap_double(x) for x in ["location_ID",
                   "genome_build", "chromosome", "position", "strand"]]) + ") "
    command = 'INSERT INTO "location"' + cols + "VALUES " + \
                  '(?,?,?,?,?)'
    c.executemany(command, location_list)

    # Counter update
    update_counter = 'UPDATE "counters" SET "count" = ? WHERE "category" = ?'
    c.execute(update_counter, [counter, "vertex"])

    return

def bulk_update_edges(c, edges):
    """
       Given a list of tuple-formatted edge entries, this
       function inserts them into the database at the provided cursor (c).
    """
    # Extract the counter
    counter = edges.pop("counter")

    cols = " (" + ", ".join([str_wrap_double(x) for x in ["edge_ID","v1",
                   "v2", "edge_type"]]) + ") "
    command = 'INSERT INTO "edge"' + cols + "VALUES " + \
                  '(?,?,?,?)'
    c.executemany(command, edges.values())

    update_counter = 'UPDATE "counters" SET "count" = ? WHERE "category" = ?'
    c.execute(update_counter, [counter, "edge"])

    return

def process_transcript(c, transcript, gene_id, genome_build, annot_name, vertices, edges):

    exons = transcript.exons
    strand = transcript.strand
    transcript_vertices = []
    transcript_edges = []

    for i in range(0, len(exons)):
        exon = exons[i]
        left = exon.start
        right = exon.end
        v1, vertices = create_vertex(c, gene_id, genome_build,
                                     exon.chromosome, left, strand, vertices)
        transcript_vertices.append(v1)

        v2, vertices = create_vertex(c, gene_id, genome_build,
                                     exon.chromosome, right, strand, vertices)
        transcript_vertices.append(v2)

   # Iterate over vertices in order to create edges. If the transcript is on the
    # minus strand, reverse the vertex and edge lists
    if strand == "-":
         transcript_vertices = transcript_vertices[::-1]
         exons = exons[::-1]

    prev_edge_type = None
    exon_index = 0
    for i in range(0,len(transcript_vertices) - 1):
        vertex_1 = transcript_vertices[i]
        vertex_2 = transcript_vertices[i+1]

        # Try to create an edge between vertex 1 and 2
        if prev_edge_type == None or prev_edge_type == "intron":
            edge_type = "exon"

        elif prev_edge_type == "exon":
            edge_type = "intron"

        edge_id, edges = create_edge(vertex_1, vertex_2, edge_type, edges)
        transcript_edges.append(edge_id)

        if edge_type == "exon":
            # Add edge annotations to database
            add_exon_annotations_to_db(c, exons[exon_index], edge_id, annot_name)
            exon_index += 1

        prev_edge_type = edge_type
    transcript_path = ",".join(map(str,transcript_edges))

    return transcript_path, vertices, edges 


def add_exon_annotations_to_db(c, exon, exon_id, annot_name):
    """ Adds annotations from edge object to the database"""

    ignore = ["gene_id", "gene_name"]
    attributes = exon.annotations
    source = attributes['source']

    for att in attributes.keys():
        if (att in ignore) or ("gene" in att) or ("transcript" in att):
            continue
        value = attributes[att]
        cols = " (" + ", ".join([str_wrap_double(x) for x in ["ID","annot_name",
               "source", "attribute", "value"]]) + ") "
        vals = [exon_id, annot_name, source, att, value]

        command = 'INSERT OR IGNORE INTO "exon_annotations"' + cols + "VALUES " + \
                  '(?,?,?,?,?)'
        c.execute(command,vals)

    return
            
def create_edge(vertex_1, vertex_2, edge_type, edges):
    """  
       Creates a new edge with the provided information, unless a duplicate
       already exists in the 'edges' dict.
    """
    # Check if the edge exists, and return the ID if it does
    query = ",".join([str(vertex_1), str(vertex_2), edge_type])
    if query in edges.keys():
        existing_edge_id = edges[query][0]
        return existing_edge_id, edges

    # In the case of no match, create the edge 
    # Get ID number from counter
    edge_id = edges["counter"] + 1
    edges["counter"] += 1
    new_edge = (edge_id, vertex_1, vertex_2, edge_type)
    keyname = ",".join([str(vertex_1), str(vertex_2), edge_type])
    edges[keyname] = new_edge

    return edge_id, edges

def create_vertex(c, gene_id, genome_build, chromosome, pos, strand, vertices):
    """
       Creates a new vertex with the provided information, unless a duplicate 
       already exists in the database.
    """
    # Check if the vertex exists
    query = ",".join([str(gene_id), genome_build, chromosome, 
                      str(pos), strand])
    if query in vertices.keys():
        existing_vertex_id = vertices[query][0]
        return existing_vertex_id, vertices

    # In the case of no match, create the edge
    # Get ID number from counter
    vertex_id = vertices["counter"] + 1
    vertices["counter"] += 1
    new_vertex = (vertex_id, gene_id, genome_build, chromosome, pos,
                  strand)
    keyname = ",".join([str(gene_id), genome_build, chromosome, 
                        str(pos), strand])
    vertices[keyname] = new_vertex

    return vertex_id, vertices


def str_wrap_double(s):
    """ Adds double quotes around the input string """
    s = str(s)
    return '"' + s + '"'

def hms_string(sec_elapsed):
    h = int(sec_elapsed / (60 * 60))
    m = int((sec_elapsed % (60 * 60)) / 60)
    s = sec_elapsed % 60.
    return "{}:{:>02}:{:>05.2f}".format(h, m, s)

########################### Main ###########################################

def main():
    options = getOptions()
    gtf_file = options.gtf
    outprefix = options.outprefix
    annot_name = options.annot_name
    genome_build = options.genome_build
    min_length = int(options.min_length)

    # Initialize database
    db_name = outprefix + ".db"
    create_database(db_name)

    # Initialize database tables
    add_counter_table(db_name)
    add_gene_table(db_name)
    add_vertex_table(db_name)
    add_edge_table(db_name)
    add_transcript_table(db_name)
    add_genome_table(db_name, genome_build)
    add_location_table(db_name)
    add_annotation_table(db_name, "gene_annotations", "genes", "gene_ID")
    add_annotation_table(db_name, "transcript_annotations", "transcripts",
                         "transcript_ID")
    add_annotation_table(db_name, "exon_annotations", "exon", "ID")
    add_dataset_table(db_name)
    add_abundance_table(db_name)
    add_observed_start_table(db_name)
    add_observed_end_table(db_name)

    # Read in genes, transcripts, and edges from GTF file
    genes, transcripts, exons = read_gtf_file(gtf_file)
    
    # Filter transcripts by length if this option is set to a nonzero value
    if min_length > 0:
        genes, transcripts = filter_by_length(genes, transcripts, min_length)

    # Group genes and transcripts by the chromosome they are on
    chrom_genes, chrom_transcripts = organize_by_chromosome(genes, transcripts)

    # Populate the database tables
    populate_db(db_name, annot_name, chrom_genes, chrom_transcripts, exons, genome_build)


if __name__ == '__main__':
    main()