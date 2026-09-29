Own the mount table used by a running server and replace it safely at
runtime. Immutable tables are swapped under a lock while surviving stores are
shared and retired stores remain open until in-flight calls release them.
