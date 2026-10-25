param(
    [Parameter(Mandatory=$true)][string]$AppletPackage,
    [Parameter(Mandatory=$true)][string]$DeckPackage,
    [Parameter(Mandatory=$true)][string]$DesktopBin
)
$ErrorActionPreference = 'Stop'
$DesktopBin = [IO.Path]::GetFullPath($DesktopBin)
$AppletPackage = [IO.Path]::GetFullPath($AppletPackage)
$DeckPackage = [IO.Path]::GetFullPath($DeckPackage)
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$compiler = & $vswhere -latest -products '*' -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\Roslyn\csc.exe' | Select-Object -First 1
if (!$compiler) { throw 'Visual Studio C# compiler was not found.' }
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
$testDirectory = Join-Path $tempRoot ('matric-skill-applet-' + [Guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $testDirectory | Out-Null
    $runner = Join-Path $testDirectory 'VerifyNativeApplet.exe'
    & $compiler /nologo /target:exe /platform:x64 "/out:$runner" "/reference:$DesktopBin/MatricPro.dll" (Join-Path $PSScriptRoot 'VerifyNativeApplet.cs')
    if ($LASTEXITCODE) { throw 'Native applet checker compilation failed.' }
    Copy-Item -LiteralPath (Join-Path $DesktopBin 'MatricServer.exe.config') -Destination ($runner + '.config')
    & $runner $DesktopBin $AppletPackage $DeckPackage (Join-Path $testDirectory 'isolated')
    if ($LASTEXITCODE) { throw 'Native applet check failed.' }
} finally {
    $resolved = [IO.Path]::GetFullPath($testDirectory)
    if (!$resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notmatch '^matric-skill-applet-[a-f0-9]{32}$') { throw 'Unsafe native applet cleanup path.' }
    if (Test-Path -LiteralPath $resolved) { Remove-Item -LiteralPath $resolved -Recurse -Force }
}
