# Agent procedures

Canonical procedures shared by Outrage's harness integrations. Harness assets
keep their own routing metadata and capability grants, then read the applicable
procedure here at invocation time.

* [search](agents/search.md) screens store metadata before reading documents.
* [annotate](agents/annotate.md) derives one metadata value from one document.
* [backfill](agents/backfill.md) coordinates annotation across missing metadata.
