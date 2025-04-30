# Step 1: Raw Dataset Source
- See details in **collected_data Directory**

# Step 2: Data Preprocessing
- General Tokenization and Entity Matching
  - See implementation details in **preprocessing_data.py**
  - Input: **collected_data/r1_training_all.json and r2_training_all.json**
  - Output: **tokenized_data/full_cleaned.json**
- Specialized Tokenization for Table-BERT
  - See implementation details in **preprocess_BERT.py**
  - Input 1: **data/all_csv directory**
  - Input 2: **tokenized_data/full_cleaned.json**
  - Output 1: **processed_dataset/tsv_data_horizontal**
  - Output 2: **processed_dataset/tsv_data_vertical**
    - Detailed Output File

      | Syntax | Description                                                                             |
      | --- |-----------------------------------------------------------------------------------------|
      | train.tsv | Training Set (90461 rows)                                                               |
      | dev.tsv | Validation Set (12792 rows)                                                             |
      | test.tsv | Testing Set (12779 rows)                                                                |
      | small_test.tsv | Subset of test for quick testing (1998 rows)                                            |
      | simple_test.tsv | Simple claims subset from r1 (4171 rows)                                                |
      | complex_test.tsv | Complex claims subset from r2 (8608 rows)                                               |
      | meta.json | Metadata on dataset sizes, missing tables. Updated inside each call to convert_to_tsv() |

