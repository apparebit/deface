# deface: Liberate Your Posts From Facebook

*deface* cleans and consolidates posts exported through Facebook's [Download
Your Information](https://www.facebook.com/dyi) page. It fixes the broken
character encoding, removes duplicate fields, and converts to a more compact and
well-defined schema comprising only [seven record
types](https://apparebit.github.io/deface/deface.html#module-deface.model). It
also combines the posts from several archives exported from Facebook into a
single, coherent timeline.

*deface* helps extricate your content from Facebook, so that you can permanently
extricate yourself from the social network. That matters because Facebook is an
imminent threat to human rights and democracy all over the world. I made [the
case against Facebook](https://youtu.be/iYJQSfQGDEE) as an invited talk at
[Rebase](http://rebase-conf.org/2020/#technology-today-a-paucity-of-integrity-and-imagination)/[SPLASH](https://2020.splashcon.org)
in November 2020.

To install *deface*:

```shell
$ pip install deface-social
```

To run *deface*:

```shell
$ deface posts/your_posts_1.json
```

Please see [the documentation](https://apparebit.github.io/deface/) for more
information about *deface*, including on usage and background. *deface* has been
released as open source under the [Apache 2.0 license](LICENSE).
