Deface
======

*Liberate your posts from Facebook!*

*deface* ingests one or more ``posts/your_posts_n.json`` files exported through
Facebook's `Download Your Information <https://www.facebook.com/dyi>`_ page,
fixes the broken character encoding, removes duplicated fields, converts to a
more compact and well-defined schema, and prints the result in chronological
order to the console. You have a choice between pretty-printed,
newline-delimited, or plain JSON for output.

By helping to extricate your content from Facebook, *deface* helps you to
permanently extricate yourself from the social network. That matters because
Facebook is an imminent threat to human rights and democracy all over the world.
I made just that case in `an invited talk <https://youtu.be/iYJQSfQGDEE>`_ at
`Rebase
<http://rebase-conf.org/2020/#technology-today-a-paucity-of-integrity-and-imagination>`_
/ `SPLASH <https://2020.splashcon.org>`_ in November 2020.

.. sidebar:: Open Source

   *deface*'s source code is `hosted on GitHub
   <https://github.com/apparebit/deface>`_ and has been released under the
   `Apache 2.0 license
   <https://github.com/apparebit/deface/blob/boss/LICENSE>`_.

.. toctree::
   :hidden:

   self

.. toctree::
   :caption: Background

   motivation
   design

.. toctree::
   :caption: Code
   :maxdepth: 2

   changelog
   installation
   use
   testing
   api

.. toctree::
   :caption: Project Links
   :hidden:

   Source Code <https://github.com/apparebit/deface>
   Issue Tracker <https://github.com/apparebit/deface/issues>
   Package <https://pypi.org/project/deface-social/>
