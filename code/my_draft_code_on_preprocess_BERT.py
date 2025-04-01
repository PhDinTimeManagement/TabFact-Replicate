#--------------------------------How processed TSV File is generated--------------------------------#
#---------Explanation with examples of def process_file(data_dir, shuffle=False) Method---------#
#--------------------Step 1--------------------#
# Read and parse the csv files
# Extract the column headers (types) and their corresponding cell values (columns)
types = ["tournament", "top-5"]
columns = {
    "tournament": ["masters tournament", "us open", "the open championship", "pga championship", "totals"],
    "top-5": [1, 2, 2, 0, 5]
}

#--------------------Step 2--------------------#
# Extract facts and labels
facts = [
    "#tony lema;-1,-1# be in the top 5 for the #master tournament;1,0# , the #us open;2,0# , and #the open championship;3,0#",
    ...
]
labels = [1, 0, ...]

#--------------------Step 3--------------------#
# Entity linking
# Parse the facts to identify entities and their linked rows/columns in the table using regex patterns like entity_linking_pattern.

#--------------------Step 4--------------------#
# Group the parsed data into a dictionary for each CSV file
example = {
    "csv": "2-1570274-4.html.csv",
    "columns": {
        "tournament": ["masters tournament", "us open", "the open championship", "pga championship", "totals"],
        "top-5": [1, 2, 2, 0, 5]
    },
    "facts": ["#tony lema;-1,-1# be in the top 5 for the #master tournament;1,0# ..."],
    "labels": [1, ...]
}





#--------------------------------------------------Conversion to TSV--------------------------------------------------#
#------Explanation with examples of def convert_to_tsv(out_file, examples, dataset_type, meta, scan) Method------#
#--------------------Step 1--------------------#
# Clean Facts
# Replace specific entities (e.g., #tony lema;-1,-1#) with [UNK] using parse_fact:
fact_clean = "[UNK] be in the top 5 for the master tournament, the us open, and the open championship"

#--------------------Step 2--------------------#
# Tokenize Rows for Horizontal Scanning
# Generate a natural language description for each row in the table using tokenize_row:
table_cells = [
    "row 1 is : tournament is masters tournament .",
    "row 2 is : tournament is us open .",
    "row 3 is : tournament is the open championship .",
    "row 4 is : tournament is pga championship .",
    "row 5 is : tournament is totals ."
]

# Combine the tokenized rows into a single string
table_str = "row 1 is : tournament is masters tournament . row 2 is : tournament is us open . ..."

#--------------------Step 3--------------------#
# Match Facts with Table Rows
# Use the useful_column_nums and remaining_table to ensure that
# the statement references only relevant columns which are tournament

#--------------------Step 4--------------------#
# Build the TSV Line
out_items = [
    "2-1570274-4.html.csv",
    "1",  # Number of features
    "tournament",
    "row 1 is : tournament is masters tournament . row 2 is : tournament is us open ...",
    "[UNK] be in the top 5 for the master tournament , the us open , and the open championship",
    "1"  # Label
]


