Motivation
==========

This tool is the result of me manually extracting content from Facebook data
archives and getting increasingly frustrated with the omnipresent `mojibake
<https://en.wikipedia.org/wiki/Mojibake>`_ and lack of human-readable
timestamps — both of which get in the way of even browsing the raw JSON.

I won't argue for the inclusion of human-readable timestamps in what really is a
JSON-based data exchange format. But the presence of mojibake makes clear that
Facebook engineers yet moved fast and broke things yet again. In this case, the
raw JSON text contains unicode escape sequences of the form ``\u00xx``, with
``x`` being a hexadecimal digit, that encode what really should be raw UTF-8
bytes. They probably are the result of Facebook using two encoding steps instead
of one. That turns a properly spelled ``don’t`` into ``don\u00e2\u0080\u0099t``
inside the JSON post file and, after parsing as regular JSON, into a nonsensical
``donât``.

For a while, I relied on Robyn Speer's `ftfy
<https://github.com/rspeer/python-ftfy>`_ for fixing this. But then one weekend,
I got curious and started playing with character encodings, came up with what
really is a one-line work-around, and started automating further clean-up of the
data. The result is this Python package.
