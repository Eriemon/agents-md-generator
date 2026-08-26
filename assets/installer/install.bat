@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM 入口只接受 bundle 内唯一的 manifest env，确保 BAT 与 PowerShell 使用同一配置事实。
set "MANIFEST_PATH=%AGENT_INSTALLER_MANIFEST_ENV_PATH%"

REM 记录候选数量，确保后续只在唯一 manifest 通过时解析入口资源。
set /a COUNT_MANIFEST=0+0

REM 环境变量存在时只核对其显式文件，避免额外扫描引入旁路配置。
if defined MANIFEST_PATH call :record_manifest "!MANIFEST_PATH!"

REM 环境变量缺失时扫描当前 bundle，仍要求结果唯一后再选择文件。
if not defined MANIFEST_PATH for %%M in ("%~dp0*.manifest.env") do call :record_manifest "%%~fM"

REM 候选数量不为一时无法证明入口身份，立即返回配置错误码。
if !COUNT_MANIFEST! neq 1 exit /b 2

REM 固定唯一候选的绝对路径，后续 containment 与读取都围绕它进行。
set "MANIFEST_PATH=!DISCOVERED_MANIFEST!"

REM 显式路径必须留在当前 installer bundle，防止外部文件重定向入口。
for %%M in ("!MANIFEST_PATH!") do if /I not "%%~dpM"=="%~dp0" exit /b 2

REM manifest 文件不存在时没有可验证的配置来源，保持 backend 未启动状态。
if not exist "!MANIFEST_PATH!" exit /b 2

REM manifest 字段必须同时给出入口文件和 runtime 候选，确保转发目标可验证。
for /f "usebackq tokens=1,* delims==" %%A in ("!MANIFEST_PATH!") do if "%%A"=="BATCH_ENTRY" set "BATCH_ENTRY=%%B"

REM 从同一 manifest 提取 PowerShell 候选，确保调用阶段不引入未声明 runtime。
for /f "usebackq tokens=1,* delims==" %%A in ("!MANIFEST_PATH!") do if "%%A"=="POWERSHELL_CANDIDATES" set "POWERSHELL_CANDIDATES=%%B"

REM 入口字段缺失时阻断参数转发，避免把空值解释成默认路径或命令。
if not defined BATCH_ENTRY exit /b 2

REM runtime 候选缺失时无法证明 backend 身份，返回配置错误码。
if not defined POWERSHELL_CANDIDATES exit /b 2

REM manifest 指定入口必须是 bundle 内普通文件，防止调用其他目录脚本。
for %%E in ("%~dp0!BATCH_ENTRY!") do if /I not "%%~dpE"=="%~dp0" exit /b 2

REM 入口文件缺失时不执行 PowerShell，保持安装资源失败可定位。
if not exist "%~dp0!BATCH_ENTRY!" exit /b 2

REM 清空命令槽，确保本轮只记录 manifest 验证出的 PowerShell 路径。
set "COMMAND_POWERSHELL="

REM runtime 选择只接受 manifest 顺序中可解析的命令，防止未验证候选进入调用。
REM 逐个把候选送入解析子程序，确保首个可用 runtime 成为本次唯一入口。
for %%C in ("!POWERSHELL_CANDIDATES:,=" "!") do call :select_powershell "%%~C"

REM runtime 为空表示 backend 身份未验证，必须在参数转发前返回错误。
if not defined COMMAND_POWERSHELL exit /b 2

REM BAT 只转发已验证的入口、manifest 路径、用户参数和退出码。
call "!COMMAND_POWERSHELL!" -NoProfile -ExecutionPolicy Bypass -File "%~dp0!BATCH_ENTRY!" -ManifestEnvPath "!MANIFEST_PATH!" %*

REM 保存 PowerShell 的真实退出状态，避免 BAT 外壳覆盖失败原因。
set "EXIT_CODE=!ERRORLEVEL!"

REM 将统一 backend 的退出码原样交给上层调用者。
exit /b !EXIT_CODE!

REM manifest 记录子程序只接受存在的普通文件，确保候选计数可追溯。
:record_manifest

REM 不存在的 glob 结果不参与计数，避免把空匹配当作合法 manifest。
if not exist "%~1" exit /b 0

REM 每次命中只增加一个候选，唯一性由主入口统一判断。
set /a COUNT_MANIFEST+=1

REM 将命中的候选规范化为绝对路径，确保唯一性检查后的文件身份可复用。
set "DISCOVERED_MANIFEST=%~f1"

REM 子程序返回时保留主入口的候选状态，避免控制流继续执行未验证路径。
exit /b 0

REM PowerShell 选择子程序保持首个成功命令，避免重复解析或覆盖稳定选择。
:select_powershell

REM 已经锁定命令时忽略后续候选，保持 manifest 顺序语义。
if defined COMMAND_POWERSHELL exit /b 0

REM where 的解析结果作为命令可调用性的证据，确保 BAT 不执行未找到的候选。
where "%~1" >nul 2>&1

REM 未解析的候选不产生副作用，返回子程序让下一个候选继续。
if errorlevel 1 exit /b 0

REM 记录首个可解析命令，后续入口将沿用该路径。
set "COMMAND_POWERSHELL=%~1"

REM 子程序返回后继续保持已选命令，防止后续候选覆盖稳定 runtime。
exit /b 0
