# KeepToText

Convert a Google Takeout zip file containing Google Keep notes to a
directory of text files, suitable for import into systems such as Evernote
or directly import them via the Evernote API.

Use Google Takeout to get a zip file, which will contain your Keep notes: https://takeout.google.com/settings/takeout

Setup:

```
virtualenv -p python2 .
. bin/activate
pip install -r requirements.txt
```

Usage:

```
./keep_convert.py [-h] [--exporter {CintaNotes,Simulate,EvernoteAPI}]
                       [--auth-token AUTH_TOKEN] [--sandbox] [--china]
                       [--outfile OUTFILE]
                       TAKEOUT
```

Example:

```
./keep_convert.py Takeout/Keep --auth-token '<<YOUR DEV TOKEN>>'
```

You can obtain your dev token from: https://www.evernote.com/api/DeveloperToken.action

If you are unable to get a dev token because the feature is disabled, contact support.

