Implement the default read-write document store as one SQLite database with
one row per key. This module owns the schema, migrations, connections and SQL
that realise the backend-independent contract in [`outrage.store`](store.md#module-outrage.store).
