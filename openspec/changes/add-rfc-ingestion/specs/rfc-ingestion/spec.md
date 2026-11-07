# Spec Delta

## Purpose

Turns the curated RFC corpus into a searchable index of citable chunks, so that the online query
flow can retrieve passages and cite them by RFC and section.

## ADDED Requirements

### Requirement: Define the corpus in a manifest

The project SHALL define its corpus in a version-controlled manifest. Each entry SHALL record an
RFC number, its family (`http`, `tls` or `tcp`), and its title. Ingestion SHALL reject a manifest
that is malformed, contains an unknown family, or lists an RFC more than once.

#### Scenario: Valid manifest

- **WHEN** ingestion reads a manifest whose entries are all well formed and unique
- **THEN** it processes exactly the RFCs the manifest lists

#### Scenario: Duplicate RFC

- **WHEN** the manifest lists the same RFC number twice
- **THEN** ingestion fails and reports the duplicate

#### Scenario: Unknown family

- **WHEN** a manifest entry has a family other than `http`, `tls` or `tcp`
- **THEN** ingestion fails and reports the entry

### Requirement: Include obsolete RFCs in the corpus

The corpus SHALL include obsolete RFCs together with the RFCs that replaced them, so that later
retrieval work can be measured against realistic version conflicts.

#### Scenario: Obsolete pair present

- **WHEN** the manifest is inspected
- **THEN** it lists RFC 793 and RFC 9293, RFC 2616 and RFC 9110, and RFC 8446 and RFC 9846

### Requirement: Remove page furniture

Parsing SHALL remove page headers, page footers and form feeds from section text. Text that
continues across a page break SHALL read as continuous text. Documents without page breaks SHALL
parse without any change to their body text.

#### Scenario: Paginated RFC

- **WHEN** a paginated RFC is parsed
- **THEN** no section text contains a `[Page N]` footer, a running page header or a form feed

#### Scenario: Paragraph spans a page break

- **WHEN** a paragraph continues across a page break
- **THEN** its lines are adjacent in the section text, with no gap where the break was

#### Scenario: Unpaginated RFC

- **WHEN** an RFC without page breaks is parsed
- **THEN** its section text keeps the original line content

### Requirement: Identify sections across RFC layouts

Parsing SHALL identify each section's number and title in every layout used by the corpus. Section
numbers SHALL be normalized without a trailing period. Lines in tables of contents, numbered lists
that restart in body text, and wrapped body lines that begin with a number SHALL NOT be headings.

#### Scenario: Modern heading

- **WHEN** a line at the left margin reads `15.5.1.  400 Bad Request`
- **THEN** a section is identified with number `15.5.1` and title `400 Bad Request`

#### Scenario: Older heading without a trailing period

- **WHEN** a line at the left margin reads `13.1.1 Cache Correctness`
- **THEN** a section is identified with number `13.1.1` and title `Cache Correctness`

#### Scenario: Centered uppercase heading

- **WHEN** a centered line reads `1.  INTRODUCTION`
- **THEN** a section is identified with number `1` and title `INTRODUCTION`

#### Scenario: Indented heading

- **WHEN** an indented line reads `2.3.1  Trailer Protocol Negotiation` at its place in the section order
- **THEN** a section is identified with number `2.3.1`

#### Scenario: Appendix heading

- **WHEN** a line reads `Appendix B.  TCP Requirement Summary` or `A.1.  Example`
- **THEN** a section is identified with number `B` or `A.1`, and it sorts after the numbered sections

#### Scenario: Table of contents entry

- **WHEN** a table of contents lists a section
- **THEN** that line does not create a section

#### Scenario: Wrapped body line

- **WHEN** wrapped body text produces a line such as `6.1 of [RFC7231]), and those responses`
- **THEN** that line stays in the section text, and later headings are still found

#### Scenario: Numbered list in body text

- **WHEN** body text contains a list numbered `1.`, `2.`, `3.` after section 3.9 has begun
- **THEN** the list stays in the text of section 3.9

### Requirement: Keep body text with its own section

Parsing SHALL recognize unnumbered front and back matter headings, so that their content is never
attached to the preceding numbered section. The abstract SHALL be kept as a section identified by
the number `abstract`, and an unnumbered security considerations section by the number `security`.

#### Scenario: Back matter follows the last numbered section

- **WHEN** an unnumbered `Index` or `Authors' Addresses` heading follows the last numbered section
- **THEN** the text of that numbered section ends before the heading

#### Scenario: Abstract

- **WHEN** an RFC has an `Abstract` heading
- **THEN** its text is available as a section numbered `abstract`

#### Scenario: Unnumbered security considerations

- **WHEN** an older RFC has an unnumbered `Security Considerations` heading
- **THEN** its text is available as a section numbered `security`, separate from the preceding section

### Requirement: Exclude sections with little retrieval value

Ingestion SHALL exclude the status memo, copyright notice, table of contents, acknowledgments,
contributors, author addresses, index and references sections. It SHALL keep security
considerations, IANA considerations and change history sections.

#### Scenario: Boilerplate excluded

- **WHEN** an RFC is ingested
- **THEN** no chunk comes from its `Status of This Memo` or `Copyright Notice` section

#### Scenario: Numbered references excluded

- **WHEN** an RFC has sections titled `References` and `Normative References`, with or without numbers
- **THEN** no chunk comes from those sections

#### Scenario: Security considerations kept

- **WHEN** an RFC has a `Security Considerations` section
- **THEN** its text appears in the index

### Requirement: Define chunk limits in configuration

Ingestion SHALL read the embedding model's name and token limit, the target chunk size in tokens,
and the characters-per-token ratio from a version-controlled configuration. The maximum chunk size
in characters SHALL be derived from the target and the ratio, not fixed in code.

#### Scenario: Limit derived from configuration

- **WHEN** the configuration sets a target of 1,000 tokens and a ratio of 3 characters per token
- **THEN** the maximum chunk size is 3,000 characters

#### Scenario: Different embedding model

- **WHEN** the configuration changes to a model with a different token limit and ratio
- **THEN** ingestion uses the new limit with no code change

#### Scenario: Target exceeds the model limit

- **WHEN** the target chunk size is greater than the embedding model's token limit
- **THEN** ingestion fails before writing an index and reports both values

#### Scenario: Invalid configuration

- **WHEN** a configuration value is missing, is not a number where one is required, or is not positive
- **THEN** ingestion fails before writing an index and reports the value

### Requirement: Chunk along section boundaries

A section that fits the maximum chunk size SHALL become one chunk. A larger section SHALL split on
paragraph boundaries into chunks that fit the maximum, and a chunk SHALL NOT contain text from
more than one section. Sections with no body text SHALL produce no chunks.

#### Scenario: Section fits

- **WHEN** a section's text is within the maximum chunk size
- **THEN** it produces exactly one chunk with the complete section text

#### Scenario: Section exceeds the maximum

- **WHEN** a section's text exceeds the maximum chunk size
- **THEN** it produces several chunks, each within the maximum, split between paragraphs, which together contain all of its text in order

#### Scenario: Single paragraph exceeds the maximum

- **WHEN** one paragraph or figure exceeds the maximum chunk size
- **THEN** it is split between lines rather than within a line

#### Scenario: Heading with no body

- **WHEN** a section heading is followed directly by a subsection
- **THEN** that heading produces no chunk

### Requirement: Preserve line layout in chunks

Chunk text SHALL keep the line breaks and indentation of the source, so that figures and tables
remain readable.

#### Scenario: ASCII figure

- **WHEN** a section contains an ASCII diagram
- **THEN** the diagram's lines appear in the chunk with their relative indentation unchanged

### Requirement: Give each chunk a stable citable identity

Every chunk SHALL have an ID derived from its RFC number, section number and position in the
section. It SHALL record the RFC number, RFC title, family, section number and section title. The
same inputs SHALL produce the same IDs on every run.

#### Scenario: Chunk metadata

- **WHEN** a chunk is read from the index
- **THEN** it provides its ID, RFC number, RFC title, family, section number, section title and text

#### Scenario: Stable identity

- **WHEN** ingestion runs twice on the same manifest, configuration and RFC files
- **THEN** both runs produce the same chunk IDs with the same text

#### Scenario: Repeated section number

- **WHEN** two sections in one RFC share a number
- **THEN** their chunk IDs remain unique

### Requirement: Build the index atomically

Ingestion SHALL write the index so that the index path only ever holds a complete index. When a run
fails, an existing index SHALL remain unchanged and no temporary file SHALL remain.

#### Scenario: Successful build

- **WHEN** ingestion completes
- **THEN** the index path holds an index containing chunks from every RFC in the manifest

#### Scenario: Build fails

- **WHEN** a run fails after an earlier index exists
- **THEN** the earlier index is unchanged and no temporary file remains

### Requirement: Record the build configuration in the index

The index SHALL record the configuration that built it: the embedding model's name and token limit,
the target chunk size, the characters-per-token ratio, and the derived maximum chunk size.

#### Scenario: Configuration read from the index

- **WHEN** an index built by ingestion is inspected
- **THEN** it reports the configuration values used for that build

### Requirement: Fail the whole run on an incomplete corpus

Ingestion SHALL fail, with a non-zero exit code and a diagnostic naming the RFC, when any RFC in the
manifest cannot be downloaded or produces no chunks. It SHALL NOT produce a partial index.

#### Scenario: Download fails

- **WHEN** an RFC in the manifest cannot be downloaded
- **THEN** ingestion exits non-zero and names that RFC

#### Scenario: RFC produces no chunks

- **WHEN** a downloaded RFC yields no chunks
- **THEN** ingestion exits non-zero and names that RFC

### Requirement: Reuse downloaded RFCs

Ingestion SHALL download only the RFCs that are not already stored locally, and it SHALL create its
local storage directory when that directory does not exist.

#### Scenario: All RFCs stored locally

- **WHEN** every RFC in the manifest is already stored locally
- **THEN** ingestion builds the index without network access

### Requirement: Report the ingestion outcome

On success, ingestion SHALL report the number of RFCs, the number of chunks and the largest chunk
size.

#### Scenario: Summary printed

- **WHEN** ingestion completes
- **THEN** the console shows the RFC count, chunk count and largest chunk size

### Requirement: Search the index by keyword

The project SHALL provide a keyword search over the index that returns chunks with their metadata,
ranked by relevance and limited to a requested count. Matches in the section title SHALL rank above
equal matches in the body. Search SHALL accept any query text without raising.

#### Scenario: Exact term

- **WHEN** a search contains a term that appears in only one chunk
- **THEN** that chunk is returned first

#### Scenario: Title match

- **WHEN** a term appears in one chunk's section title and in another chunk's body with similar frequency
- **THEN** the chunk with the title match ranks higher

#### Scenario: Result limit

- **WHEN** more chunks match than the requested count
- **THEN** only the requested number of chunks is returned

#### Scenario: Query with punctuation

- **WHEN** a search contains punctuation or operators, such as `Content-Length` or `"HTTP/2`
- **THEN** it returns results normally, or no results, and does not raise

#### Scenario: No matches

- **WHEN** no chunk matches the query
- **THEN** an empty result is returned

#### Scenario: Missing index

- **WHEN** a search is run and the index does not exist
- **THEN** it reports a diagnostic, and it does not create an index
