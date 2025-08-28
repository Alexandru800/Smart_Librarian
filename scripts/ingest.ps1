<# Build the Chroma collection from data/book_summaries.json #>
$ErrorActionPreference = "Stop"

# Activate venv if present
if (Test-Path "$PSScriptRoot\..\.\venv\Scripts\Activate.ps1") {
    . "$PSScriptRoot\..\.\venv\Scripts\Activate.ps1"
}

# Run ingest
python -m app.rag.ingest
