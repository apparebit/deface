Motivation
==========

This tool is the result of me manually extracting content from Facebook data
archives and getting increasingly frustrated about the omnipresent
[mojibake](https://en.wikipedia.org/wiki/Mojibake) as well as lack of
human-readable timestamps, both of which get in the way of browsing the raw
JSON.

I won't argue for the inclusion of human-readable timestamps in what really is a
JSON-based data exchange format. But the presence of mojibake makes clear that
Facebook engineers moved fast, broke things, and couldn't be bothered to fix the
mess they created. In this particular case, the mess are several unicode escape
sequences ``\u00xx`` in a row that encode what really should be raw UTF-8 bytes
in the file. They are the result of Facebook using two independent encoding
steps of a single one. That turns, say, ``don’t`` into
``don\u00e2\u0080\u0099t`` inside the JSON exported from Facebook. When naively
parsing the file as JSON, it now reads ``donât``.

Originally, I relied on `Robyn Speer's ftfy
<https://github.com/rspeer/python-ftfy>`_. But then one weekend I got curious
and started playing with character encodings, came up with what really is a
one-line work-around, and started automating further clean-up of the data.
Several weeks later, this package was ready for primetime.
