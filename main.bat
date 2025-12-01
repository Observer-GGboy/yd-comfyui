@echo off
REM main.bat

setlocal enabledelayedexpansion

set "RegistryPath=HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
set "VersionRequired=14.40.33810.00"
set "InstalledVersion="

for /f "tokens=2*" %%A in ('reg query "%RegistryPath%" /v Version 2^>nul ^| findstr Version') do (
    set "InstalledVersion=%%B"
)

if "!InstalledVersion:~0,1!"=="v" (
    set "InstalledVersion=!InstalledVersion:~1!"
)

if "!InstalledVersion!"=="" (
    echo 未检测到 Microsoft Visual C++ Redistributable，正在自动安装...
    goto InstallVC
) else (
    echo 检测到当前安装版本：!InstalledVersion!
    for /f "tokens=1-4 delims=." %%A in ("!InstalledVersion!") do (
        set Major=%%A
        set Minor=%%B
        set Build=%%C
        set Revision=%%D
    )
    
    for /f "tokens=1-4 delims=." %%A in ("%VersionRequired%") do (
        set ReqMajor=%%A
        set ReqMinor=%%B
        set ReqBuild=%%C
        set ReqRevision=%%D
    )

    if !Major! LSS !ReqMajor! goto VersionCheckFailed
    if !Major! EQU !ReqMajor! if !Minor! LSS !ReqMinor! goto VersionCheckFailed
    if !Major! EQU !ReqMajor! if !Minor! EQU !ReqMinor! if !Build! LSS !ReqBuild! goto VersionCheckFailed
    if !Major! EQU !ReqMajor! if !Minor! EQU !ReqMinor! if !Build! EQU !ReqBuild! if !Revision! LSS !ReqRevision! goto VersionCheckFailed
)

goto SkipInstall

:VersionCheckFailed
echo 当前版本 !InstalledVersion! 低于要求版本 %VersionRequired%
goto InstallVC

:InstallVC
if "!InstalledVersion!"=="" (
    echo 正在静默安装 Microsoft Visual C++ 2022 Redistributable...
) else (
    echo 正在升级 Microsoft Visual C++ 2022 Redistributable...
)
start /wait VC_redist.x64.exe /install /quiet /norestart
IF %ERRORLEVEL% NEQ 0 (
    echo 安装失败，请手动安装后再试。
    pause
    exit /b 1
)
echo 安装成功，继续启动程序...

:SkipInstall
echo 运行库版本检查通过（当前版本：!InstalledVersion!，要求版本：%VersionRequired%）
..\python312\python.exe -s aix.py --listen 0.0.0.0 --windows-standalone-build
pause