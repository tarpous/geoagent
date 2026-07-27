# Launch llama-server against a local GGUF on the host GPU.
# Weights are not committed; download with the Hugging Face CLI into models/llm/.
param(
    [string]$ModelPath = "",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8080,
    [int]$NCtx = 16384,
    [int]$NGpuLayers = 99
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
if (-not $ModelPath) {
    $ModelPath = Join-Path $Root "models\llm\demo.gguf"
}

if (-not (Test-Path $ModelPath)) {
    Write-Error "Missing GGUF at $ModelPath. Set -ModelPath or place the demo GGUF under models/llm/."
}

$llama = Get-Command llama-server -ErrorAction SilentlyContinue
if (-not $llama) {
    Write-Error "llama-server not found on PATH. Build/install llama.cpp CUDA binaries first."
}

& $llama.Source `
    --model $ModelPath `
    --host $HostAddress `
    --port $Port `
    --ctx-size $NCtx `
    --n-gpu-layers $NGpuLayers `
    --jinja
