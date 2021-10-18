Testing
=======

To perform end-to-end testing of *deface*, I am using my own Facebook posts as
captured in 10 archives exported over three years and comprising a total of
17,000 exported posts representing roughly 6,700 posts I actually made. The
ample redundancy in my test corpus allows me to track how Facebook changes the
post archive format. Overall, the structure of the JSON has not changed much.
Yet attention to detail is critical because Facebook did change (1) what fields
it exports, (2) how it encodes those fields, and (3) what values fields have.

Since preserving user data is a critical requirement for *deface*, Facebook
changing field values may make it impossible to converge on a single merged
value. Thankfully, so far, I have only encountered such changes in ancillary
fields with automatically generated content, such as the title of a post varying
between "Robert Grimm" and "Robert Grimm updated his status". Since post titles
*are* automatically generated, preserving their variations seems like
unnecessary bloat. Since one of the variations is a prefix of the other, the
longer variation is the obvious choice. It has the added benefit of minimizing
information loss.

For now, I am *not* making this corpus publicly available. First, some of those
posts were private, only visible to close friends. Second, I have since deleted
most posts from Facebook, including the public ones. I will still report summary
statistics on how well *deface* does when processing the corpus and will update
the statistics as I work towards zero errors and zero redundant posts with the
same timestamp.

You can also easily run your own experiments with, say, your own Facebook post
data. By default, the *deface* command line tool prints errors and warnings as
single-line comments (starting with ``//``) to standard error and only then
prints the cleaned up and simplified JSON output to standard out. The *deface*
command also collects basic summary statistics and prints them before exiting.

When ingesting post data, *deface* processes one post at a time. It reports an
error when the raw Facebook post data diverges from its expected ad-hoc schema
or when a cleaned-up record in *deface*'s schema does not merge with another
record that obviously describes the same entity (typically as determined by a
URL). In either case, *deface* drops the post as erroneous. After ingesting all
input files, *deface* also warns about posts sharing the same second-resolution
timestamps. Occassionally, such posts are distinct posts indeed. But more often
than not, they are variations of the same post, differing in a detail that
*deface* does not yet handle.

.. attention::

   My own test corpus comprises 10 Facebook archives exported between August
   2018 and September 2021. They contain a total of 17,000 posts, roughly 6,700
   of which are unique.

   *deface* currently reports 305 malformed posts and exports 8,198 cleaned-up
   posts. It also warns that 2,444 posts share 1,170 timestamps with other
   posts.
