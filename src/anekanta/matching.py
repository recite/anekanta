"""Author/year matching for the baseline extractor."""

import re


def author_year_pattern(author, year, coauthor=None):
    """Match one surname or an explicit pair of surnames in publication order."""
    if coauthor is not None:
        # PDF text can retain a line-ending hyphen in either surname.
        first, second = (
            r"(?:-\s+)?".join(map(re.escape, name)) for name in (author, coauthor)
        )
        return (
            rf"(?<!\w){first}\s+(?:and|&)\s+{second}"
            rf"(?:,\s*|\s*\(\s*|\s+){re.escape(year)}[a-z]?(?!\w)"
        )
    return re.escape(author) + r"\s?(et al\.)?,?\s?" + re.escape(year)


def split_sentences(text):
    """Split text at likely sentence boundaries.

    Reference:
    http://stackoverflow.com/questions/8465335/a-regex-for-extracting-
           sentence-from-a-paragraph-in-python
    """
    sentence_enders = re.compile(
        r"""
        # Split sentences on whitespace between them.
        (?:               # Group for two positive lookbehinds.
          (?<=[.!?])      # Either an end of sentence punct,
        | (?<=[.!?]['"])  # or end of sentence punct and quote.
        )                 # End group of two positive lookbehinds.
        (?<!  Mr\.   )    # Don't end sentence on "Mr."
        (?<!  Mrs\.  )    # Don't end sentence on "Mrs."
        (?<!  Jr\.   )    # Don't end sentence on "Jr."
        (?<!  Dr\.   )    # Don't end sentence on "Dr."
        (?<!  Prof\. )    # Don't end sentence on "Prof."
        (?<!  Sr\.   )    # Don't end sentence on "Sr."
        (?<!  Sen\.  )
        (?<!  Ms\.   )
        (?<!  Rep\.  )
        (?<!  Gov\.  )
        (?<!  et\ al\.  )
        (?<!  i\.e\.  )
        (?<!  U\.S\.  )
        (?<!  p\.  )      # Don't end sentence on "p." (page)
        \s+               # Split on whitespace between sentences.
        """,
        re.IGNORECASE | re.VERBOSE,
    )
    return sentence_enders.split(text)
