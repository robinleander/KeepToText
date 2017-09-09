# KeepToText

Convert a Google Takeout zip file containing Google Keep notes to a
directory of text files, suitable for import into systems such as Evernote

Use Google Takeout to get a zip file, which will contain your Keep notes
**NOTE**: Be sure that *only* Keep files are included in the Google Takeout zip file, not contacts or any other Google data

Usage:
  python keepToText.py zipfile

The text files will be placed in a directory called Text, under the same
directory as the zip file. You may import that folder into Evernote.

Works with Python 2 or 3
