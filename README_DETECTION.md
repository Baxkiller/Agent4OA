# 内容检测服务

面向老年人的内容安全检测服务，提供虚假信息检测、毒性内容检测和隐私泄露检测功能。

## 功能概述

### 1. 虚假信息/诈骗识别
- **输入**: 信息链接（短视频链接或文章链接）或文本内容
- **输出**: 识别结果（是否为虚假信息/诈骗，认定理由和证据）
- **实现方法**: 
  - 对于视频：爬取网络视频，按1frame/1s切分，提取音频转文字，组合送入大模型分析
  - 对于文章：爬取文章内容，直接送入大模型分析
  - 对于文本：直接送入精心组织的prompt，传递给大模型

### 2. 毒性内容识别
- **输入**: 待检测文本内容
- **输出**: 识别结果（是否为毒性内容，毒性类别和严重程度）
- **实现方法**: 结合detoxify机器学习模型和大模型，提供更准确的检测结果

### 3. 隐私泄露检测
- **输入**: 待检测文本内容
- **输出**: 检测结果（是否为隐私泄露，隐私类型和风险等级）
- **实现方法**: 结合正则表达式、命名实体识别(NER)和大模型，多层次检测隐私信息

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 环境配置

复制配置文件模板：
```bash
cp config.env.example .env
```

编辑`.env`文件，设置必要的环境变量：
```bash
# 必须设置OpenAI API密钥
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 安装额外依赖

对于视频处理功能，需要安装ffmpeg：
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载ffmpeg并添加到PATH
```

对于中文NLP功能，安装spaCy中文模型：
```bash
python -m spacy download zh_core_web_sm
```

## 启动服务

### 方法1: 使用启动脚本
```bash
python run_server.py
```

### 方法2: 直接使用uvicorn
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后，访问以下地址：
- API文档: http://localhost:8000/docs
- 服务信息: http://localhost:8000/

## API使用说明

### 1. 虚假信息检测

#### 从URL检测
```bash
curl -X POST "http://localhost:8000/api/detection/fake-news/url" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com/news-article",
       "user_id": "user123"
     }'
```

#### 从文本检测
```bash
curl -X POST "http://localhost:8000/api/detection/fake-news/text" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "这是一条可能的虚假新闻内容...",
       "user_id": "user123"
     }'
```

### 2. 毒性内容检测

```bash
curl -X POST "http://localhost:8000/api/detection/toxic-content" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "待检测的文本内容...",
       "user_id": "user123"
     }'
```

### 3. 隐私泄露检测

```bash
curl -X POST "http://localhost:8000/api/detection/privacy-leak" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "我的电话是13812345678，邮箱是test@example.com",
       "user_id": "user123"
     }'
```

### 4. 综合检测

```bash
curl -X POST "http://localhost:8000/api/detection/comprehensive" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "待检测的文本内容...",
       "user_id": "user123"
     }'
```

## 响应格式

所有API都返回统一的响应格式：

```json
{
  "success": true,
  "message": "检测完成",
  "data": {
    "result_id": "fake_news_20240101_120000_123456",
    "detection_type": "fake_news",
    "content_text": "检测的内容...",
    "is_detected": false,
    "confidence_score": 0.85,
    "reasons": ["检测理由1", "检测理由2"],
    "evidence": ["支撑证据1", "支撑证据2"],
    "created_at": "2024-01-01T12:00:00",
    "user_id": "user123"
  }
}
```

### 虚假信息检测特有字段
```json
{
  "video_frames": ["frame_0001.jpg", "frame_0002.jpg"],
  "audio_transcript": "视频音频转录内容",
  "fact_check_sources": ["建议核查的来源"]
}
```

### 毒性内容检测特有字段
```json
{
  "toxicity_categories": {
    "hate_speech": 0.1,
    "threat": 0.05,
    "harassment": 0.2
  },
  "severity_level": "low"
}
```

### 隐私泄露检测特有字段
```json
{
  "privacy_types": ["phone", "email"],
  "sensitive_entities": [
    {
      "type": "phone",
      "value": "138****5678",
      "risk_level": "high"
    }
  ],
  "risk_level": "medium"
}
```

## 技术架构

### 核心组件

1. **ContentCrawler**: 内容爬取服务
   - 支持视频下载和处理
   - 支持网页内容提取
   - 音频转文字功能

2. **FakeNewsDetector**: 虚假信息检测器
   - 基于大模型的内容分析
   - 支持多媒体内容处理
   - 提供详细的检测报告

3. **ToxicContentDetector**: 毒性内容检测器
   - 结合detoxify模型和大模型
   - 多维度毒性分析
   - 支持中文内容检测

4. **PrivacyLeakDetector**: 隐私泄露检测器
   - 正则表达式模式匹配
   - 命名实体识别(NER)
   - 大模型语义分析

5. **DetectionManager**: 检测服务管理器
   - 统一管理各检测器
   - 支持并行检测
   - 综合风险评估

### 依赖的开源项目

- **detoxify**: 毒性内容检测的机器学习模型
- **yt-dlp**: 视频下载工具
- **spaCy**: 自然语言处理库
- **OpenAI**: 大语言模型API
- **FastAPI**: Web框架
- **BeautifulSoup**: 网页解析
- **moviepy**: 视频处理
- **speech_recognition**: 语音识别

## 性能优化

### 1. 缓存策略
- 对相同内容的检测结果进行缓存
- 减少重复的API调用

### 2. 并行处理
- 综合检测时并行执行多种检测
- 提高整体检测效率

### 3. 资源管理
- 及时清理临时文件
- 限制视频下载大小和时长

## 安全考虑

### 1. 输入验证
- 严格验证输入参数
- 防止恶意URL和内容注入

### 2. 隐私保护
- 对检测到的敏感信息进行脱敏
- 不存储用户的原始内容

### 3. 访问控制
- 支持用户身份验证
- API访问频率限制

## 监控和日志

### 1. 日志记录
- 详细的操作日志
- 错误和异常追踪

### 2. 性能监控
- API响应时间监控
- 资源使用情况监控

### 3. 健康检查
- 提供健康检查接口
- 服务状态监控

## 部署建议

### 1. 生产环境
- 使用HTTPS协议
- 配置反向代理(Nginx)
- 设置适当的CORS策略

### 2. 容器化部署
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run_server.py"]
```

### 3. 环境变量
- 生产环境中使用环境变量管理配置
- 不要在代码中硬编码敏感信息

## 故障排除

### 常见问题

1. **OpenAI API调用失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 检查API配额是否充足

2. **视频下载失败**
   - 检查ffmpeg是否正确安装
   - 确认视频URL是否有效
   - 检查网络连接和防火墙设置

3. **模型加载失败**
   - 检查依赖包是否正确安装
   - 确认模型文件是否完整
   - 检查系统资源是否充足

### 日志分析
- 查看应用日志: `tail -f app.log`
- 检查错误信息和堆栈跟踪
- 根据错误类型采取相应的解决措施

## 贡献指南

欢迎贡献代码和建议！请遵循以下步骤：

1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件
- 参与讨论 