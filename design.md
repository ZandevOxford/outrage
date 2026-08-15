# Rage design

## Components

### MCP server

Python implemented MCP server primarily for use in local mode.

Provides access to the data store.

### Data store

Python library for storing data used by the MCP server.

Data is stored in an SQLite database local to the current project.

### Skills

Appropriate skills and/or agent definitions.

Initially to support Claude Code.

## Key namespace

The key namespace is an arbitrary string, with period delimiters. A colon instead of a period indicates metadata.

For example:

* context.<guid>.task  could contain a summary of the task for a particular context
* context.<guid>.design  could contain a design document
* context.<guid>.design:title  could contain the title of the design document
* project.reference.implementation  could contain the implementation notes for the project

If A.B.C exists then A and A.B implicitly exist with no content.

## Values

Values are strings which should either be markdown or json.

## Tools

* Retrieve document: retrieves the content of a document. Optionally specify a character range. Optionally specify a search pattern and index to start the read from.
* Store document: stores document or metadata at a key.
* List keys: List keys immediately under a key, including subkeys and metadata.
* Get documents: Get multiple documents or metadata, with a key and or metadata filter. It should be possible to for example list the titles of all documents under a key.

## Schema

This can be stored in a single table, with an index on the key.
