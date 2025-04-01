#------------------How LPA Tokenization Processes Data for Latent Program Search------------------#
#------------------------------------------Step 1------------------------------------------#
# Parsing the Table
# Read the CSV file for each table
# Extract column names and determine data types (num or str)
Columns: ["round", "clubs involved", ...]
Mapping: {"round": "str", "clubs involved": "num", ... : ...}

#------------------------------------------Step 2------------------------------------------#
# Extracting Facts and Labels
Facts = [
    "the highest number of winner from a #previous round;0,3# in the #turkish cup;-1,-1# be #54;3,2# in #round;0,0# 3",
    ...
]
Labels: [1, ...]

#------------------------------------------Step 3------------------------------------------#
# Entity Masking
# Identify entities (e.g., #entity_name;row,column#) in facts
# Replace these with placeholders (<ENTITYX>)
Raw: "the highest number of winner from a #previous round;0,3# in the #turkish cup;-1,-1# be #54;3,2# in #round;0,0# 3"
Masked: "the highest number of winner from a <ENTITY0> in the <ENTITY1> be <ENTITY2> in <ENTITY3> 3"

#------------------------------------------Step 4------------------------------------------#
# Part-of-Speech (POS) Tagging
# Tag each word in the masked fact with its POS
Tagged: "DT JJS NN IN NNS IN DT <ENTITY0> IN DT <ENTITY1> VBD <ENTITY2> IN <ENTITY3> CD"

#------------------------------------------Step 5------------------------------------------#
# Build Structured Entries
[
    "2-1859269-1.html.csv",
    "the highest number of winner from a #previous round;0,3# in the #turkish cup;-1,-1# be #54;3,2# in #round;0,0# 3",
    "DT JJS NN IN NNS IN DT ENT IN DT ENT VBD ENT IN ENT CD",
    "the highest number of winner from a <ENTITY0> in the <ENTITY1> be <ENTITY2> in <ENTITY3> 3",
    [],
    [["clubs involved",54],["tmp_input",3]],
    ["winners from previous round","round"],
    ["clubs involved"],
    "nt-1",
    1
  ],

#------------------------------------------Step 6------------------------------------------#
# Create Vocabulary Entries for Entities
# Map entities and terms in the facts to unique numerical IDs for efficient processing during latent program search
{"round;0,3#": 8799,
"cup;-1,-1#": 1049,
"#54;3,2#": 29899,
"round;0,0#": 18057}





