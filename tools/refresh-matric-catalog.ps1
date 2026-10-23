param([Parameter(Mandatory=$true)][string]$DesktopBin, [string]$MatricSourceCommit = "unknown", [string]$OutputPath)
$ErrorActionPreference = 'Stop'
if (!$OutputPath) { $OutputPath = Join-Path $PSScriptRoot '../skills/matric-decks/references/catalog.json' }
$DesktopBin = [IO.Path]::GetFullPath($DesktopBin)
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$compiler = & $vswhere -latest -products '*' -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\Roslyn\csc.exe' | Select-Object -First 1
if (!$compiler) { throw 'Visual Studio C# compiler was not found.' }
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
$testDirectory = Join-Path $tempRoot ('matric-catalog-' + [Guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $testDirectory | Out-Null
    $runner = Join-Path $testDirectory 'ExportMatricCatalog.exe'
    & $compiler /nologo /target:exe /platform:x64 "/out:$runner" /reference:System.Drawing.dll "/reference:$DesktopBin/MatricPro.dll" "/reference:$DesktopBin/Newtonsoft.Json.dll" (Join-Path $PSScriptRoot 'ExportMatricCatalog.cs')
    if ($LASTEXITCODE) { throw 'Catalog exporter compilation failed.' }
    Get-ChildItem -LiteralPath $DesktopBin -Filter '*.dll' | Copy-Item -Destination $testDirectory
    Copy-Item -LiteralPath (Join-Path $DesktopBin 'MatricServer.exe.config') -Destination ($runner + '.config')
    $assemblyHash = (Get-FileHash -LiteralPath (Join-Path $DesktopBin 'MatricPro.dll') -Algorithm SHA256).Hash.ToLowerInvariant()
    & $runner $OutputPath $MatricSourceCommit $assemblyHash
    if ($LASTEXITCODE) { throw 'Catalog export failed.' }
} finally {
    $resolved = [IO.Path]::GetFullPath($testDirectory)
    if (!$resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^matric-catalog-[a-f0-9]{32}$') { throw 'Unsafe catalog cleanup path.' }
    if (Test-Path -LiteralPath $resolved) { Remove-Item -LiteralPath $resolved -Recurse -Force }
}
