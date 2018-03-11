# KeepToText

Convert a Google Takeout zip file containing Google Keep notes to a
directory of text files, suitable for import into systems such as Evernote

Use Google Takeout to get a zip file, which will contain your Keep notes

**NOTE**: Be sure that *only* Keep files are included in the Google Takeout zip file, not contacts or any other Google data

Usage:
  usage: keepToText.py [-h] [--encoding ENCODING] [--system-encoding] zipFile

The text files will be placed in a directory called Text, under the same
directory as the zip file. You may import that folder into Evernote.

Works with Python 2 or 3

Options:
  Use the --encoding option to specify an output encoding, for example, --encoding latin_1
  Use --system-encoding option to use your operating system's current encoding
  The default output encoding is utf-8
    
