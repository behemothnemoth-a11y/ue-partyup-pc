# Development guidance

Keep repository private until the owner explicitly approves publication. NEVER include bug reports, captures, device-address logs, local selection files or credentials in commits.

Hardware-verified compatibility is the tested pair of EVERBOOMs only. The software supports up to ten selected members and an opt-in source-backed legacy adapter; treat larger groups and all other models as unverified until tested. Do not send guessed opcodes, firmware commands or resets. Use captured protocol evidence, match acknowledgements, close transports and report partial failures honestly. Hardware tests affect playback; tell the user before running a stop/restart sequence.

Run `python -m unittest discover -s tests -v`. Record hardware checks separately in docs/TESTING.md; do not convert software tests into hardware compatibility claims.
