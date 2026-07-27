# Launch vLLM OpenAI-compatible server for the serving / ablation profile.
param(
    [string]$ModelId = "Qwen/Qwen3.5-9B",
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [int]$MaxModelLen = 16384,
    [string]$Quantization = "awq"
)

$ErrorActionPreference = "Stop"
$vllm = Get-Command vllm -ErrorAction SilentlyContinue
if (-not $vllm) {
    Write-Error "vllm not found on PATH. Install/run vLLM in an approved container or env first."
}

& $vllm.Source serve $ModelId `
    --host $HostAddress `
    --port $Port `
    --max-model-len $MaxModelLen `
    --quantization $Quantization
