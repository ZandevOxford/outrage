Read one or many Parquet parts as a document store through DuckDB. The
backend accepts arbitrarily ordered parts without building a corpus-sized
resident index, trading some read latency for bounded process memory.
