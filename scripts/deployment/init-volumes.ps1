# Initialize Docker volumes with data from host directories
Write-Host "Initializing Docker volumes with host data..." -ForegroundColor Yellow

# Get current directory
$currentDir = (Get-Location).Path

# Create temporary containers to copy data
$volumesToInit = @(
    @{Name="temp_files"; HostPath="$currentDir\temp_files"},
    @{Name="chroma_db"; HostPath="$currentDir\chroma_db"},
    @{Name="logs"; HostPath="$currentDir\logs"}
)

foreach ($vol in $volumesToInit) {
    $volumeName = "embedder_$($vol.Name)"
    $hostPath = $vol.HostPath
    
    if (Test-Path $hostPath) {
        Write-Host "Copying data from $hostPath to volume $volumeName..." -ForegroundColor Green
        
        # Create a temporary container to copy data
        docker run --rm -v "${volumeName}:C:/data" -v "${hostPath}:C:/source" mcr.microsoft.com/windows/servercore:ltsc2019 powershell -Command "
            if (Test-Path 'C:/source') {
                Copy-Item -Path 'C:/source/*' -Destination 'C:/data/' -Recurse -Force -ErrorAction SilentlyContinue
            }
        "
    } else {
        Write-Host "Skipping $hostPath - directory does not exist" -ForegroundColor Yellow
    }
}

Write-Host "Volume initialization completed!" -ForegroundColor Green