# Step 1: Raw Dataset Source
- All the text are lower-cased, containing foreign characters in some tables. 

- There are two files:
  - **Single-hop (r1)** is collected in the first round (simple channel), which contains sentences involving less reasoning. 
  - **Multi-hop (r2)** is collected in the second round (complex channel), which involves more complex multi-hop reasoning.
  - These two files in total contains roughly 110K statements
  - The positive and negative satements are balanced