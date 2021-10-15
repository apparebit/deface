Motivation
==========

This tool is the result of me manually extracting content from Facebook data
archives and getting increasingly frustrated about the omnipresent `mojibake
<https://en.wikipedia.org/wiki/Mojibake>`_ as well as lack of human-readable
timestamps, both of which get in the way of browsing the raw JSON.

I won't argue for the inclusion of human-readable timestamps in what really is a
JSON-based data exchange format. But the presence of mojibake makes clear that
Facebook engineers moved fast, broke things, and couldn't be bothered to fix the
mess they created. In this case, the mess involves unicode escape sequences of
the form ``\u00xx`` that encode what really should be raw UTF-8 bytes. They are
the result of Facebook using two encoding steps where one would be just right.
That turns ``don’t`` into ``don\u00e2\u0080\u0099t`` inside Facebook's JSON
files and, after parsing the JSON, into a nonsensical ``donât``.

I originally relied on `Robyn Speer's ftfy
<https://github.com/rspeer/python-ftfy>`_. But then one weekend I got curious
and started playing with character encodings, came up with what really is a
one-line work-around, and started automating further clean-up of the data. The
result is this Python package.
