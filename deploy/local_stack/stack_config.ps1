$stackConfig = [ordered]@{
    RepoRoot = 'G:\check\myworld\Scripts\backup 1-5 toi-uu'
    PythonPath = 'C:\Python314\python.exe'
    FlutterPath = 'G:\check\myworld\Scripts\flutter_windows_3.41.4-stable\flutter\bin\flutter.bat'
    NginxRoot = 'G:\nginx-1.28.3\nginx-1.28.3'
    NginxTemplatePath = 'G:\check\myworld\Scripts\backup 1-5 toi-uu\deploy\nginx\nginx.conf'
    DockerDesktopPath = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    NgrokCommand = 'ngrok'
    PublicHost = 'aiagentvmu.id.vn'
    PublicScheme = 'https'
    DjangoHost = '127.0.0.1'
    DjangoPort = 8000
    NginxPort = 8888
    CollaboraPort = 9980
    ManualEditProvider = 'collabora'
    CollaboraEditorPath = '/browser/dist/cool.html'
    ManualEditWopiSrcBaseUrl = 'http://host.docker.internal:8888'
    ManualEditSessionTtlSeconds = '3600'
    CollaboraContainerName = 'collabora-code'
    CollaboraImage = 'collabora/code'
    CollaboraSslTermination = $true
    WordAgentToken = 'dev-local-token-123'
    RunMigrateOnLaunch = $true
    RunCollectstaticOnLaunch = $true
    IncludeFrontendBuildWindow = $false
    IncludeWordWorkerWindow = $true
    PrepareWordAddinBeforeStart = $false
}

$stackConfig['PublicUrl'] = '{0}://{1}' -f $stackConfig.PublicScheme, $stackConfig.PublicHost
$stackConfig['BackendBaseUrl'] = 'http://{0}:{1}/api' -f $stackConfig.DjangoHost, $stackConfig.DjangoPort
$stackConfig['FlutterProjectRoot'] = Join-Path $stackConfig.RepoRoot 'flutter_frontend'
$stackConfig['NginxExecutablePath'] = Join-Path $stackConfig.NginxRoot 'nginx.exe'
$stackConfig['LiveNginxConfPath'] = Join-Path $stackConfig.NginxRoot 'conf\nginx.conf'
$stackConfig['WordWorkerStartScriptPath'] = Join-Path $stackConfig.RepoRoot 'deploy\word_worker_direct_host\start_word_worker_agent.ps1'
$stackConfig['WordWorkerBuildScriptPath'] = Join-Path $stackConfig.RepoRoot 'deploy\word_worker_direct_host\build_native_word_addin.ps1'
$stackConfig['WordWorkerInstallScriptPath'] = Join-Path $stackConfig.RepoRoot 'deploy\word_worker_direct_host\install_native_word_addin.ps1'

[pscustomobject]$stackConfig
