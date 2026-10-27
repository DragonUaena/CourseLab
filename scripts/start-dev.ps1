$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "请先在项目根目录创建 .venv 并运行: python -m pip install -e `".[dev]`""
}
if (-not (Test-Path -LiteralPath (Join-Path $root "frontend\node_modules"))) {
    throw "请先进入 frontend 并运行: npm install"
}
if (-not (Test-Path -LiteralPath (Join-Path $root ".env"))) {
    Copy-Item -LiteralPath (Join-Path $root ".env.example") -Destination (Join-Path $root ".env")
}

Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit", "-Command", "Set-Location -LiteralPath '$root'; & '$python' -m uvicorn app.main:app --reload"
Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoExit", "-Command", "Set-Location -LiteralPath '$root\frontend'; npm run dev"
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5173"

