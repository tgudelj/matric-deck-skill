param([Parameter(Mandatory=$true)][string]$Package, [Parameter(Mandatory=$true)][string]$DesktopBin)
$ErrorActionPreference = 'Stop'
$DesktopBin = [IO.Path]::GetFullPath($DesktopBin)
$Package = [IO.Path]::GetFullPath($Package)
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$compiler = & $vswhere -latest -products '*' -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\Roslyn\csc.exe' | Select-Object -First 1
if (!$compiler) { throw 'Visual Studio C# compiler was not found.' }
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
$testDirectory = Join-Path $tempRoot ('matric-skill-import-' + [Guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $testDirectory | Out-Null
    $runner = Join-Path $testDirectory 'VerifyNativeImport.exe'
    & $compiler /nologo /target:exe /platform:x64 "/out:$runner" "/reference:$DesktopBin/MatricPro.dll" (Join-Path $PSScriptRoot 'VerifyNativeImport.cs')
    if ($LASTEXITCODE) { throw 'Native import checker compilation failed.' }
    Get-ChildItem -LiteralPath $DesktopBin -Filter '*.dll' | Copy-Item -Destination $testDirectory
    Copy-Item -LiteralPath (Join-Path $DesktopBin 'MatricServer.exe.config') -Destination ($runner + '.config')
    & $runner $Package (Join-Path $testDirectory 'collections')
    if ($LASTEXITCODE) { throw 'Native import check failed.' }
} finally {
    $resolved = [IO.Path]::GetFullPath($testDirectory)
    if (!$resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^matric-skill-import-[a-f0-9]{32}$') { throw 'Unsafe native import cleanup path.' }
    if (Test-Path -LiteralPath $resolved) { Remove-Item -LiteralPath $resolved -Recurse -Force }
}
