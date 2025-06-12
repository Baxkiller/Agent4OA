# 加载环境变量的PowerShell脚本
# 使用方法: .\load_env.ps1

# 检查是否存在.env文件
if (Test-Path ".env") {
    Write-Host "正在加载 .env 文件中的环境变量..." -ForegroundColor Green
    
    # 读取.env文件并设置环境变量
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # 移除可能存在的引号
            $value = $value.Trim('"').Trim("'")
            
            # 设置环境变量
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Set-Item -Path "env:$name" -Value $value
            
            Write-Host "  设置环境变量: $name" -ForegroundColor Yellow
        }
    }
    
    Write-Host "环境变量加载完成!" -ForegroundColor Green
} else {
    Write-Host "错误: .env 文件不存在!" -ForegroundColor Red
    Write-Host "请先复制 config.env.example 为 .env 并填入您的API密钥" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "操作步骤:" -ForegroundColor Cyan
    Write-Host "1. 复制文件: Copy-Item config.env.example .env" -ForegroundColor White
    Write-Host "2. 编辑 .env 文件，设置您的 OPENAI_API_KEY" -ForegroundColor White
    Write-Host "3. 运行此脚本: .\load_env.ps1" -ForegroundColor White
}

# 验证API密钥是否设置
if ($env:OPENAI_API_KEY) {
    $maskedKey = $env:OPENAI_API_KEY.Substring(0, [Math]::Min(10, $env:OPENAI_API_KEY.Length)) + "***"
    Write-Host "✓ OPENAI_API_KEY 已设置: $maskedKey" -ForegroundColor Green
} else {
    Write-Host "✗ OPENAI_API_KEY 未设置!" -ForegroundColor Red
} 