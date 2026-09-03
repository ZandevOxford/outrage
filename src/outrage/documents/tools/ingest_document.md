Convert one local file to Markdown and store it as an Outrage document.

The source must be a regular file on the server's filesystem. URLs and other
non-file sources are refused. Conversion uses MarkItDown's built-in converters
through `convert_local`; plugins, remote fetching, Azure services and LLM
conversion options are not enabled.

The optional `documents` extra must be installed. Existing destinations are
preserved unless `overwrite` is true. A dry run performs the conversion and
reports its result without writing the document or its title.
