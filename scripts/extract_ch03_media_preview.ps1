$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PreviewDir = Join-Path $Root "output\ch03_rag_engine\word_media_preview"
$MediaDir = Join-Path $PreviewDir "media"
$PngDir = Join-Path $PreviewDir "png"
New-Item -ItemType Directory -Force -Path $MediaDir, $PngDir | Out-Null

$docx = Join-Path $PreviewDir "ch03_source.docx"
if (-not (Test-Path -LiteralPath $docx)) {
  & py -c "import shutil, sys; from pathlib import Path; sys.path.insert(0, 'scripts'); import extract_ch02_ch03_word_assets as ex; shutil.copy2(ex.CHAPTERS['ch03']['docx'], Path(r'$docx'))"
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.Drawing

$zip = [System.IO.Compression.ZipFile]::OpenRead($docx)
try {
  foreach ($entry in $zip.Entries) {
    if (-not $entry.FullName.StartsWith("word/media/")) { continue }
    $name = Split-Path $entry.FullName -Leaf
    $out = Join-Path $MediaDir $name
    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $out, $true)
    $png = Join-Path $PngDir ([IO.Path]::GetFileNameWithoutExtension($name) + ".png")
    try {
      $img = [System.Drawing.Image]::FromFile($out)
      $img.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
      $img.Dispose()
    } catch {
      Copy-Item -LiteralPath $out -Destination $png -Force
    }
  }
} finally {
  $zip.Dispose()
}

$images = Get-ChildItem -LiteralPath $PngDir -Filter "*.png" | Sort-Object {
  if ($_.BaseName -match "image(\d+)") { [int]$Matches[1] } else { 9999 }
}

$thumbW = 220
$thumbH = 150
$labelH = 28
$cols = 4
$rows = [Math]::Ceiling($images.Count / $cols)
$sheet = New-Object System.Drawing.Bitmap ($cols * $thumbW), ($rows * ($thumbH + $labelH))
$graphics = [System.Drawing.Graphics]::FromImage($sheet)
$graphics.Clear([System.Drawing.Color]::White)
$font = New-Object System.Drawing.Font "Arial", 10
$brush = [System.Drawing.Brushes]::Black

for ($i = 0; $i -lt $images.Count; $i++) {
  $img = [System.Drawing.Image]::FromFile($images[$i].FullName)
  $col = $i % $cols
  $row = [Math]::Floor($i / $cols)
  $x = $col * $thumbW
  $y = $row * ($thumbH + $labelH)
  $scale = [Math]::Min(($thumbW - 12) / $img.Width, ($thumbH - 12) / $img.Height)
  $w = [Math]::Max(1, [int]($img.Width * $scale))
  $h = [Math]::Max(1, [int]($img.Height * $scale))
  $dx = $x + [int](($thumbW - $w) / 2)
  $dy = $y + 6
  $graphics.DrawImage($img, $dx, $dy, $w, $h)
  $graphics.DrawString($images[$i].BaseName, $font, $brush, $x + 8, $y + $thumbH + 4)
  $img.Dispose()
}

$sheetPath = Join-Path $PreviewDir "ch03_media_contact_sheet.png"
$sheet.Save($sheetPath, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$sheet.Dispose()

Write-Host $sheetPath
