# Document contents
0 0

### *class* outrage.contents.ContentsResult(source_key: str, metadata_key: str, headings: int, source_characters: int, source_bytes: int, characters: int)
543 543

#### source_key *: str*
1175 1175

#### metadata_key *: str*
1305 1305

#### headings *: int*
1448 1448

#### source_characters *: int*
1559 1559

#### source_bytes *: int*
1706 1706

#### characters *: int*
1919 1919

### outrage.contents.make_contents(opened: Store, key: str, \*, metadata_name: str = 'contents', strip_links: bool = True) → ContentsResult
2070 2070

### outrage.contents.render_contents(markdown: str, \*, strip_links: bool = True) → str
3281 3283

### outrage.contents.render_html_contents(html: str) → str
4344 4348
