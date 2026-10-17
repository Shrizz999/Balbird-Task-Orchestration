# PowerShell script to sign Stauff v12 executables with a corporate certificate
param (
    [string]$PublisherName = "Balbird Industries"
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  BALBIRD TASK ORCHESTRATOR - CODE SIGNING SCRIPT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check if a code signing certificate already exists in CurrentUser\My
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object { $_.Subject -like "*$PublisherName*" } | Select-Object -First 1

if (-not $cert) {
    Write-Host "Creating a new self-signed Code Signing Certificate for '$PublisherName'..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=$PublisherName, O=Balbird Industries, C=IN" `
        -KeySpec Signature `
        -KeyUsage DigitalSignature `
        -FriendlyName "$PublisherName Code Signing" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(5)
    
    # Also trust it locally on this machine
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store "Root", "CurrentUser"
    $rootStore.Open("ReadWrite")
    $rootStore.Add($cert)
    $rootStore.Close()
    Write-Host "Certificate created and added to your CurrentUser Root store." -ForegroundColor Green
} else {
    Write-Host "Found existing Code Signing Certificate: $($cert.Thumbprint)" -ForegroundColor Green
}

# 2. Export public certificate (.cer) for distribution to friends/employees
$exportPath = Join-Path (Get-Location) "dist\Balbird_Certificate.cer"
Export-Certificate -Cert $cert -FilePath $exportPath -Force | Out-Null
Write-Host "Exported public certificate to: $exportPath" -ForegroundColor Green
Write-Host "-> Anyone installing this .cer into 'Trusted Root Certification Authorities' will trust all signed Balbird apps without warnings!" -ForegroundColor Gray

# 3. Sign the executables
$exes = @(
    "dist\Stauff Admin Dashboard v14.exe",
    "dist\Stauff Task Updater v14.exe"
)

foreach ($exe in $exes) {
    if (Test-Path $exe) {
        Write-Host "Signing $exe..." -ForegroundColor Yellow
        $result = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -ErrorAction SilentlyContinue
        if ($result.Status -eq "Valid") {
            Write-Host "  [OK] Successfully signed $exe" -ForegroundColor Green
        } else {
            # Retry without timestamp server if internet / timestamp server was unreachable
            $result = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert
            Write-Host "  [OK] Signed (offline): $($result.StatusMessage)" -ForegroundColor Green
        }
    } else {
        Write-Host "  [WARNING] File not found: $exe" -ForegroundColor Red
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  CODE SIGNING COMPLETE!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
