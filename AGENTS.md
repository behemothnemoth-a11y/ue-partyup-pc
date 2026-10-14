# Development guidance

Keep repository private until the owner explicitly approves publication. NEVER include bug reports, captures, device-address logs, local selection files or credentials in commits.

Model compatibility is EVERBOOM only. Treat all other model support as unverified. Do not send guessed opcodes, firmware commands or resets. Use captured protocol evidence, match acknowledgements, close transports and report partial failures honestly. Hardware tests affect playback; tell the user before running a stop/restart sequence.

Run `python -m unittest discover -s tests -v`. Record hardware checks separately in docs/TESTING.md; do not convert software tests into hardware compatibility claims.
