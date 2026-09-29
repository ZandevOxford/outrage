# Document contents
0 0 1

### *class* outrage.contents.ContentsResult(source_key: str, metadata_key: str, headings: int, source_characters: int, source_bytes: int, characters: int)
695 695 14

#### source_key *: str*
1327 1327 20

#### metadata_key *: str*
1457 1457 24

#### headings *: int*
1600 1600 28

#### source_characters *: int*
1711 1711 32

#### source_bytes *: int*
1858 1858 36

#### characters *: int*
2071 2071 41

### outrage.contents.make_contents(opened: Store, key: str, \*, metadata_name: str = 'contents', strip_links: bool = True) → ContentsResult
2222 2222 45

### outrage.contents.render_contents(markdown: str, \*, strip_links: bool = True) → str
3457 3459 63

### outrage.contents.render_html_contents(html: str) → str
4549 4553 80
