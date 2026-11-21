# Data license and attribution

The audio and transcripts in `data/raw/` and `data/cleaned/` (and the derived `data/splits/`)
come from the **NST Danish ASR Database (16 kHz) – reorganized version**, distributed by
Språkbanken at the National Library of Norway:

- Resource: <https://www.nb.no/sprakbanken/ressurskatalog/oai-nb-no-sbr-55/> (sbr-55,
  hdl:21.11146/55), files `lydfiler_16_1.tar.gz` (channel 1 audio of the training part dan0565)
  and `ADB_OD_DAN_0565.tar.gz` (its metadata), downloaded 2026-11-21.
- License: **Creative Commons Zero (CC0 1.0)** ("CC Zero (fri bruk)" on the resource page),
  <https://creativecommons.org/publicdomain/zero/1.0/>. Rights holder: Nasjonalbiblioteket.
- Origin: recorded in 2000 by Nordisk Språkteknologi (NST); reorganized by Språkbanken in 2013,
  test part converted in 2021.

Changes we made: we selected a subset of sentence recordings (see `scripts/01_download.py`);
raw WAV files are byte-identical to the archive (not committed, rebuilt by the script; SHA-256 in
`data/raw/CHECKSUMS.sha256`); cleaned files are filtered and losslessly converted to 16-bit FLAC,
as logged in `data/cleaning_log.csv`.

This data license is separate from the code license in `LICENSE` (MIT), which covers only our code.
