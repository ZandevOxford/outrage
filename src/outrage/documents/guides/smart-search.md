# Smart search

**Experimental.** It works, but it is new and its tuning has barely begun:
its results, its tuning file, its options and its configuration may still
change in a minor release, which the stable interfaces of 1.0 do not.

Smart search finds the documents under a key that are about a plain-language
query, without bringing their text into the agent's context. A small
classification model judges each document in a cascade - its title, then its
keywords, summary, contents and finally its body - and moves to the next level
only while the evidence leaves it unsure.

## Configure a model

The judge speaks the System One protocol. TypeSafe's hosted Jev is the
default; give it a key with `TYPESAFE_API_KEY`, and optionally
`TYPESAFE_BASE_URL` and `TYPESAFE_DEFAULT_MODEL`. The same settings can live
in `~/.outrage/config.toml`, which must be readable only by its owner:

```toml
[smart_search]
key = "..."
# base_url = "https://api.typesafe.ai"
# model = "jev-latest"
```

Environment variables take precedence over the file. The base URL is the API
root; Outrage appends `/v1/systemone`. A local compatible server such as
`laya-serve` needs no key.

## Search from the command line

```text
outrage smart-search "how are PostgreSQL stores backed up?"
outrage smart-search "release checks" plans
```

Every document not ruled out is printed, best first, with its probability,
its decision and the level that decided it. `--evidence` adds what each level
said.

**A search covers one slice.** `--limit` (100 by default) bounds how many
documents are judged, since each costs a request, and stderr names the
`--after` key for the next slice. Each probability is the document's own, so
results from several slices can be merged by sorting.

`--level title --level summary` keeps a search to metadata, sending no
document's body.

## Enable it for agents

**A search sends metadata and document text to the configured service.** So
the MCP `smart_search` tool is off by default even when a key is configured.
Opt in with:

`outrage init --smart-search`

or `outrage config --smart-search`, which records the flag on the server
entry. The command line search needs no opt-in.

## Getting good results

Smart search works from the same metadata a title survey does, so it is only
as good as that metadata. Missing metadata never rules a document out - it is
carried forward to the next level - but a store whose documents have
`!title` and `!summary` is judged cheaply and well. The `outrage-backfill`
agent fills in missing summaries.

## Tuning

The levels, the questions asked at each, the scoring constants and the request
sizes are a packaged file, [`outrage/smart-search/tuning`](../smart-search/tuning.json).
[`outrage/smart-search/readme`](../smart-search/readme.md) says what each part
means and how to tune it.

## Reference

* [Command line](../cli.md#smart-search) - `outrage smart-search`.
* [Tools](../tools.md) - `smart_search`.
