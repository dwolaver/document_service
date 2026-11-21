"""RFC question answering: ingest RFCs into a keyword index and answer questions from them."""

import logging

# The library logs, but never decides where records go. Without a handler of its own, Python's
# last-resort handler would print any warning to standard error in a program that hasn't configured
# logging. A program that wants the records configures logging, and a command does with -v.
logging.getLogger(__name__).addHandler(logging.NullHandler())
