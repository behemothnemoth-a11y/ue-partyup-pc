param([string]$Python = '.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& $Python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; no build made.' }
& $Python -m PyInstaller --noconfirm PartyUpPC.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
Write-Output 'Private build: dist\PartyUpPC\PartyUpPC.exe. No settings or device logs are bundled.'
