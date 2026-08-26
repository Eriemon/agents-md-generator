#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$ManifestEnvPath,
    [string]$Platform,
    [string]$SkillSource,
    [string]$TargetRoot,
    [string]$ProjectKind,
    [Alias("Replace")]
    [switch]$IsReplace,
    [Alias("Yes")]
    [switch]$IsYes,
    [Alias("DryRun")]
    [switch]$IsDryRun
)

# 从 bundle manifest 读取 backend 配置，保证入口与 manifest 使用同一文件事实。
$pathManifest = $ManifestEnvPath

# 环境变量只在参数为空时补充 manifest 路径，避免覆盖调用者的显式选择。
if ([string]::IsNullOrWhiteSpace($pathManifest)) {

    # 将环境变量提供的 manifest 路径绑定为本次入口唯一事实，后续资源检查都围绕该文件展开。
    $pathManifest = $env:AGENT_INSTALLER_MANIFEST_ENV_PATH
}

# 仅当调用者与环境都未给出路径时扫描 bundle，避免静默选择旁路配置。
if ([string]::IsNullOrWhiteSpace($pathManifest)) {

    # 收集 bundle 内的 manifest 候选，后续分支要求恰好保留一个。
    $listManifestCandidates = @(Get-ChildItem -LiteralPath $PSScriptRoot -File -Filter "*.manifest.env")

    # 候选数量异常时阻止任何 backend 调用，避免选择不确定的配置。
    if ($listManifestCandidates.Count -ne 1) {

        # 返回 bundle 配置错误，调用方可据此修复安装资源。
        Write-Host "> ERR: [PowerShell] exactly one manifest env candidate is required in the installer bundle."

        # 退出码 2 表示入口配置失败且 backend 尚未启动。
        exit 2
    }

    # 采用唯一候选的绝对路径，后续所有资源解析都绑定同一文件。
    $pathManifest = $listManifestCandidates[0].FullName
}

# 规范化 manifest 路径，保证后续 containment 比较使用绝对路径。
$pathManifest = [IO.Path]::GetFullPath($pathManifest)

# 记录 installer bundle 根，限制 manifest 与 backend 的可达范围。
$pathInstallerRoot = [IO.Path]::GetFullPath($PSScriptRoot)

# 目录分隔前缀把根目录边界变成可重复比较的字符串条件，避免相似路径误通过。
$pathInstallerRootPrefix = $pathInstallerRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar

# 拒绝 bundle 外 manifest，防止外部文件重定向入口配置。
if (-not $pathManifest.StartsWith($pathInstallerRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {

    # 输出 containment 错误，说明 manifest 尚未进入 backend 处理。
    Write-Host "> ERR: [PowerShell] manifest env escapes the installer bundle."

    # 退出码 2 保持与其他入口边界错误一致。
    exit 2
}

# manifest 文件不存在时不允许继续执行外部 backend。
if (-not (Test-Path -LiteralPath $pathManifest -PathType Leaf)) {

    # 返回明确错误而不是让后续 ConvertFrom-StringData 抛出泛化异常。
    Write-Host "> ERR: [PowerShell] installer manifest is missing: $pathManifest"

    # 退出码表示入口尚未执行任何 backend 副作用。
    exit 2
}

# 将受管键值转换为只读映射，防止 manifest 内容成为可执行输入。
$listManifestLines = @(Get-Content -LiteralPath $pathManifest)

# 仅提取键名而不解释值，让重复键检查在任何字典覆盖行为发生前完成。
$listManifestKeys = @($listManifestLines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { ($_ -split '=', 2)[0] })

# 汇总重复键名，避免后续字典解析悄悄覆盖先前配置。
$listDuplicateManifestKeys = @($listManifestKeys | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object { $_.Name })

# 重复键会让 ConvertFrom-StringData 覆盖旧值，因此在映射建立前终止入口。
if ($listDuplicateManifestKeys.Count -gt 0) {

    # 返回配置完整性错误，避免继续使用不确定的键值。
    Write-Host "> ERR: [PowerShell] manifest env contains duplicate keys: $($listDuplicateManifestKeys -join ',')"

    # 退出码 2 表示 manifest 解析没有产生 backend 副作用。
    exit 2
}

# 将唯一键行转换为映射，后续投影比较读取的就是这份冻结字段集合。
$manifestValues = ($listManifestLines -join [Environment]::NewLine) | ConvertFrom-StringData

# 使用 .NET 内置摘要实现，避免 Windows PowerShell 缺少可选 cmdlet 时产生非零噪声。
function Get-ManifestSha256 {
    param([string]$Path)

    # 创建摘要提供器并在 finally 释放，避免文件身份检查依赖可变的外部命令。
    $pathSha256 = [Security.Cryptography.SHA256]::Create()

    # 在摘要计算边界内保留真实异常，finally 负责释放算法资源。
    try {
        return [BitConverter]::ToString($pathSha256.ComputeHash([IO.File]::ReadAllBytes($Path))).Replace("-", "").ToLowerInvariant()
    }

    # 无论摘要成功或失败都释放 .NET 哈希对象，避免资源泄漏。
    finally {
        $pathSha256.Dispose()
    }
}

# env 的相对路径声明必须指向本次解析到的入口文件。
$strManifestEnvRelative = [string]$manifestValues.MANIFEST_ENV_RELATIVE_PATH

# env 文件名偏离当前入口时阻止从其他 bundle 读取配置。
if ([string]::IsNullOrWhiteSpace($strManifestEnvRelative) -or $strManifestEnvRelative -ne [IO.Path]::GetFileName($pathManifest)) {
    Write-Host "> ERR: [PowerShell] manifest env path does not match the launcher resource."

    # 绑定失败时返回配置错误，backend 仍保持未调用状态。
    exit 2
}

# env 与 JSON manifest 必须由摘要绑定，防止单独替换任一入口配置。
$pathSkillRootRelative = [string]$manifestValues.SOURCE_ROOT_RELATIVE

# 没有 Skill 根声明时无法建立 JSON 与源目录的可信边界。
if ([string]::IsNullOrWhiteSpace($pathSkillRootRelative)) {
    Write-Host "> ERR: [PowerShell] installer manifest is missing SOURCE_ROOT_RELATIVE."

    # 源根字段缺失会使所有后续路径失去 containment 依据，因此此分支以 2 结束解析。
    exit 2
}

# 将 manifest 的源根相对路径解析为后续 containment 的绝对边界。
$pathSkillRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $pathSkillRootRelative))

# 记录 JSON manifest 的相对资源名，Join-Path 将据此构造 Skill 根内的唯一文件目标。
$pathManifestJsonRelative = [string]$manifestValues.MANIFEST_JSON_RELATIVE_PATH

# 读取 JSON manifest 摘要，后续只接受内容完全匹配的文件。
$strManifestHash = [string]$manifestValues.MANIFEST_SHA256

# JSON 身份字段不完整时，入口无法证明目标文件属于当前 bundle。
if ([string]::IsNullOrWhiteSpace($pathManifestJsonRelative) -or [string]::IsNullOrWhiteSpace($strManifestHash)) {
    Write-Host "> ERR: [PowerShell] installer manifest is missing JSON identity fields."

    # 配置不完整时退出，确保 backend 没有副作用。
    exit 2
}

# 解析 JSON manifest 的绝对路径，后续文件读取只使用这个受控目标。
$pathManifestJson = [IO.Path]::GetFullPath((Join-Path $pathSkillRoot $pathManifestJsonRelative))

# JSON manifest 必须位于 Skill 根且为普通文件，拒绝路径重定向。
if (-not $pathManifestJson.StartsWith($pathSkillRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $pathManifestJson -PathType Leaf)) {
    Write-Host "> ERR: [PowerShell] configured installer JSON manifest is missing or outside the Skill root."

    # containment 失败时不读取外部 JSON，也不调用 backend。
    exit 2
}

# 用 env 摘要核对 JSON 内容，防止入口绑定指向过期资源。
if ((Get-ManifestSha256 -Path $pathManifestJson) -ne $strManifestHash.ToLowerInvariant()) {
    Write-Host "> ERR: [PowerShell] installer JSON manifest hash mismatch."

    # 摘要不匹配意味着 JSON 身份已失效，保持事务尚未创建的失败边界。
    exit 2
}

# 读取 JSON 投影对象；下面逐项与 env 对照，防止配置文件被单独改写。
$jsonManifest = Get-Content -Raw -LiteralPath $pathManifestJson | ConvertFrom-Json

# 将 JSON 声明的 bundle 根解析为绝对路径，验证入口目录的身份。
$pathExpectedBundle = [IO.Path]::GetFullPath((Join-Path $pathSkillRoot ([string]$jsonManifest.bundle_root_relative)))

# bundle 根与脚本目录不一致时拒绝继续使用投影字段。
if ($pathExpectedBundle -ne $pathInstallerRoot) {
    Write-Host "> ERR: [PowerShell] bundle root does not match the JSON manifest."

    # 目录身份失败时 backend 不得启动。
    exit 2
}

# 记录 JSON 计算出的 env 绝对位置，用来与实际 manifest 路径做身份等式比较。
$pathExpectedManifest = [IO.Path]::GetFullPath((Join-Path $pathInstallerRoot $strManifestEnvRelative))

# env 位置偏离 JSON 记录的文件时，配置替换已经无法被可信链路证明。
if ($pathExpectedManifest -ne $pathManifest) {
    Write-Host "> ERR: [PowerShell] manifest env path does not match the JSON manifest."

    # 路径绑定失败时不进入 backend。
    exit 2
}

# 取得 JSON 的 env 投影节点，后续只接受它声明的字段集合。
$dictEnvProjection = $jsonManifest.env_projection

# 投影节点确保 env 键值可回溯到结构字段；缺失时没有可验证的字段映射。
if ($null -eq $dictEnvProjection) {
    Write-Host "> ERR: [PowerShell] JSON manifest env_projection is missing."

    # JSON 结构缺陷时保持零安装副作用。
    exit 2
}

# 构造允许的 env 键集合，并保留两个摘要键作为身份扩展字段。
$listAllowedEnvKeys = @($dictEnvProjection.psobject.Properties.Name) + @("MANIFEST_SHA256", "MANIFEST_PROJECTION_SHA256")

# 记录投影允许集合之外的键名，非空结果就是 env 混入未声明输入的证据。
$listUnknownEnvKeys = @($manifestValues.Keys | Where-Object { $_ -notin $listAllowedEnvKeys })

# 未声明键集合记录 env 相对 JSON 合同的增量；非空就是输入边界被扩大。
if ($listUnknownEnvKeys.Count -gt 0) {
    Write-Host "> ERR: [PowerShell] manifest env contains undeclared keys: $($listUnknownEnvKeys -join ',')"

    # 键集合失败表示输入合同被破坏，返回前不允许调用 Python backend。
    exit 2
}

# 对每个投影属性执行来源追踪，确保 env 值能回溯到 JSON 节点。
foreach ($propertyProjection in $dictEnvProjection.psobject.Properties) {

    # 每个字段从完整 JSON 对象重新开始，避免沿用上一字段的中间值。
    $objectProjectedValue = $jsonManifest

    # 沿点号路径读取当前字段对应的 JSON 值。
    foreach ($strPathSegment in ([string]$propertyProjection.Value -split '\.')) {

        # 当前字段的路径片段来自 projection，更新游标以确保所得对象与 env 值一一对应。
        $objectProjectedValue = $objectProjectedValue.$strPathSegment
    }

    # 数组投影使用逗号串作为 env 规范表示，避免 PowerShell 隐式格式化差异。
    if ($objectProjectedValue -is [System.Array]) {

        # 统一数组字符串化方式，避免比较时出现隐式格式差异。
        $objectProjectedValue = ($objectProjectedValue -join ',')
    }

    # 双侧属性值不等时终止，避免 backend 继续使用失去绑定的路径或命令参数。
    if ([string]$manifestValues.($propertyProjection.Name) -ne [string]$objectProjectedValue) {
        Write-Host "> ERR: [PowerShell] manifest env projection mismatch: $($propertyProjection.Name)"

        # 字段校验失败时不允许 backend 使用不一致配置。
        exit 2
    }
}

# 解析投影 TSV 的绝对路径，后续仍以 installer bundle 为 containment 边界。
$pathManifestProjection = [IO.Path]::GetFullPath((Join-Path $pathInstallerRoot ([string]$manifestValues.MANIFEST_PROJECTION_RELATIVE_PATH)))

# 读取投影 TSV 摘要，确保投影文件与 env 身份字段成对绑定。
$strManifestProjectionHash = [string]$manifestValues.MANIFEST_PROJECTION_SHA256

# 投影文件必须存在于 bundle 内，禁止 manifest 指向外部资源。
if (-not $pathManifestProjection.StartsWith($pathInstallerRootPrefix, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $pathManifestProjection -PathType Leaf)) {
    Write-Host "> ERR: [PowerShell] manifest projection is missing or outside the installer bundle."

    # containment 失败时不读取投影表。
    exit 2
}

# 用 env 摘要核对投影 TSV 内容，防止资源与配置脱钩。
if ([string]::IsNullOrWhiteSpace($strManifestProjectionHash) -or (Get-ManifestSha256 -Path $pathManifestProjection) -ne $strManifestProjectionHash.ToLowerInvariant()) {
    Write-Host "> ERR: [PowerShell] manifest projection hash mismatch."

    # 摘要失败时不启动 backend。
    exit 2
}

# 读取投影行，后续验证摘要头、列结构和唯一键。
$listProjectionLines = @(Get-Content -LiteralPath $pathManifestProjection)

# 最小投影结构由摘要头、列头和数据起始行共同组成，用于确保表格身份与来源绑定。
if ($listProjectionLines.Count -lt 4 -or $listProjectionLines[1] -ne "# manifest_json_sha256=$strManifestHash") {
    Write-Host "> ERR: [PowerShell] manifest projection JSON binding is invalid."

    # 投影结构校验失败时停止解析，避免把不完整表格交给 backend。
    exit 2
}

# 用集合记录已经验证的投影键，拒绝重复行覆盖字段。
$setProjectionKeys = @{}

# 进入逐行验证阶段，将每条 TSV 记录限制为固定三列合同。
foreach ($strProjectionLine in $listProjectionLines[3..($listProjectionLines.Count - 1)]) {

    # 把当前 TSV 行固定拆成三个字段，后续重复键与值一致性检查共享同一解析结果。
    $listProjectionFields = $strProjectionLine -split "`t", 3

    # 列数错误或重复键会使投影无法一一对应。
    if ($listProjectionFields.Count -ne 3 -or $setProjectionKeys.ContainsKey($listProjectionFields[0])) {
        Write-Host "> ERR: [PowerShell] manifest projection contains an invalid or duplicate row."

        # 行合同失败时停止解析后续字段。
        exit 2
    }

    # 记录当前键，下一行不能再次声明同一字段。
    $setProjectionKeys[$listProjectionFields[0]] = $true

    # 当前键的 TSV 值与 env 不同，说明生成物身份已经漂移，必须阻断安装。
    if (-not $manifestValues.ContainsKey($listProjectionFields[0]) -or [string]$manifestValues[$listProjectionFields[0]] -ne [string]$listProjectionFields[2]) {
        Write-Host "> ERR: [PowerShell] manifest projection value mismatch: $($listProjectionFields[0])"

        # 投影行失败时返回配置错误，避免继续调用 backend。
        exit 2
    }
}

# 使用 manifest 的 backend 相对路径，避免入口复制安装实现位置。
$pathBackendRelative = [string]$manifestValues.BACKEND_RELATIVE_PATH

# listPythonCandidates 记录 manifest 允许的 runtime；空列表保持配置错误而不补默认值。
$listPythonCandidates = @([string]$manifestValues.PYTHON_CANDIDATES -split ',') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

# 未声明 backend 时返回可修复的配置错误。
if ([string]::IsNullOrWhiteSpace($pathBackendRelative)) {

    # 入口不能猜测或拼写 Python 文件路径。
    Write-Host "> ERR: [PowerShell] installer manifest is missing BACKEND_RELATIVE_PATH."

    # 退出码表示配置不完整且未启动 backend。
    exit 2
}

# backend 必须位于当前 Skill 根内，避免 manifest 把入口引向外部程序。
$pathBackend = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $pathBackendRelative))

# 预计算 Skill 根前缀，使 backend containment 比较不误判相似目录名。
$pathSkillRootPrefix = $pathSkillRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar

# 外部路径或缺失文件都在调用 Python 前拒绝，避免配置重定向执行。
if (-not $pathBackend.StartsWith($pathSkillRootPrefix, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $pathBackend -PathType Leaf)) {

    # 将 containment 失败标记为可修复的 manifest 路径错误。
    Write-Host "> ERR: [PowerShell] configured installer backend is missing or outside the Skill root."

    # 退出码表示 Python 尚未被调用。
    exit 2
}

# 按 manifest 顺序选择可用解释器，所有业务参数原样交给统一 backend。
$commandPython = $null

# 逐项解析候选的真实命令路径，避免把未验证的文本交给调用运算符。
foreach ($strPythonCandidate in $listPythonCandidates) {

    # 将 manifest 的候选文本解析为命令对象，后续版本探针只作用于真实解析结果。
    $commandObjectPython = Get-Command $strPythonCandidate.Trim() -ErrorAction SilentlyContinue

    # 当前候选通过解析后写入命令路径，后续不再猜测其他值。
    if ($null -ne $commandObjectPython) {

        # 对占位命令执行版本探针，避免把 WindowsApps 别名当作真实 runtime。
        & $commandObjectPython.Source --version *> $null

        # 版本探针退出码非零时只淘汰当前候选，不污染后续候选状态。
        if ($LASTEXITCODE -ne 0) {

            # 版本探针失败只淘汰当前候选，保留 manifest 规定的 runtime 选择顺序。
            continue
        }

        # commandPython 绑定 manifest 顺序中的首个解析路径，backend 后续只用该值。
        $commandPython = $commandObjectPython.Source

        # 已锁定解释器，避免同一次安装混用多个 runtime。
        break
    }
}

# 没有解释器时不进行参数拼接或文件写入。
if ([string]::IsNullOrWhiteSpace($commandPython)) {

    # 调用者应先准备 manifest 声明的 runtime。
    Write-Host "> ERR: [PowerShell] no configured Python candidate is available for the installer backend."

    # 退出码表示解释器缺失且没有文件副作用。
    exit 2
}

# 组装参数数组，避免拼接字符串造成路径或用户输入重新解析。
$listBackendArguments = @("$pathBackend", "--bundle-root", "$PSScriptRoot", "--manifest-env-path", "$pathManifest")

# 子进程也必须使用已经验证的 env 路径，不能回退到目录猜测。
$env:AGENT_INSTALLER_MANIFEST_ENV_PATH = $pathManifest

# 可选平台参数只在调用者明确提供时转发。
if (-not [string]::IsNullOrWhiteSpace($Platform)) {

    # 将调用者平台值交给 backend 的哈希投影校验。
    $listBackendArguments += @("--platform", $Platform)
}

# 可选源目录只在调用者明确提供时转发。
if (-not [string]::IsNullOrWhiteSpace($SkillSource)) {

    # backend 负责源目录 containment 和 Skill 身份检查。
    $listBackendArguments += @("--skill-source", $SkillSource)
}

# 可选目标根只在调用者明确提供时转发。
if (-not [string]::IsNullOrWhiteSpace($TargetRoot)) {

    # 让 backend 复核目标根存在性及 containment，入口不生成目录。
    $listBackendArguments += @("--target-root", $TargetRoot)
}

# 可选项目类型只在调用者明确提供时转发。
if (-not [string]::IsNullOrWhiteSpace($ProjectKind)) {

    # backend 在任何文件操作前执行 Skill-only guard。
    $listBackendArguments += @("--project-kind", $ProjectKind)
}

# 替换开关保持显式传递，默认不覆盖已有安装。
if ($IsReplace) {

    # backend 仍要求已有目标的最终确认。
    $listBackendArguments += "--replace"
}

# 非交互确认只在调用者明确选择时传递。
if ($IsYes) {

    # 将显式确认标记传给 backend，避免无意覆盖已有目标。
    $listBackendArguments += "--yes"
}

# dry-run 只读取配置并输出诊断，不触发复制事务。
if ($IsDryRun) {

    # backend 保留 dry-run 的零副作用合同。
    $listBackendArguments += "--dry-run"
}

# 入口只转发到统一 backend，退出码保持原样返回给 BAT 或调用者。
& $commandPython @listBackendArguments

# 保存 backend 退出码，防止 PowerShell 入口掩盖失败。
$exitCodeInstaller = $LASTEXITCODE

# 将原始退出码返回给 BAT 或上层调用者。
exit $exitCodeInstaller
