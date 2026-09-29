Implement a read-only document store as one sorted Parquet file using
PyArrow. It is built in one pass for large reference corpora, keeps only small
index columns resident and loads document content lazily by row group.
