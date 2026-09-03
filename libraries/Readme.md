# Folder structure

Each manufacturer gets its own folder.
Generate both file formats per catalog. You can use the **--convert-meta** flag to convert between json and csv or dump
both during sw<->hsm conversion.

```
\<manufacturer>
    |-<...>.py # scripts for converting pdfs etc.
    |-output/ # for artifacts (hsmlib, csv), ignored by gitignore.
```