# Agent4OA 老年人内容安全检测服务 API 文档

## 概述

Agent4OA 是一个面向老年人的内容安全检测服务，提供毒性内容检测、虚假信息检测、隐私泄露检测等功能。系统支持分离式配置管理，子女和老年人可以独立配置检测参数，并提供详细的检测报告功能。

**服务地址**: `http://localhost:8000`  
**版本**: 2.1.0  
**文档**: `http://localhost:8000/docs` (Swagger UI)

---

## 1. 服务基本信息

### GET `/`
获取服务基本信息

**请求格式**: 无参数

**响应格式**:
```json
{
  "service": "老年人内容安全检测服务",
  "version": "2.1.0",
  "description": "支持文本和视频的统一内容检测，包括协同配置和检测报告功能",
  "endpoints": {
    "docs": "/docs",
    "detect_toxic": "/detect/toxic",
    "detect_fake_news": "/detect/fake_news",
    "detect_privacy": "/detect/privacy",
    "cache_status": "/cache/status",
    "config_prompts": "/config/prompts",
    "config_parent": "/config/parent",
    "config_elderly": "/config/elderly",
    "detection_report": "/reports/detection"
  }
}
```

---

## 2. 内容检测 API

### POST `/detect/toxic`
检测毒性内容

**请求格式**:
```json
{
  "content": "要检测的文本内容或抖音链接",
  "user_id": "用户ID（可选）"
}
```

**响应格式**:
```json
{
  "success": true,
  "message": "检测完成",
  "data": {
    "is_toxic_for_elderly": false,
    "confidence": 0.95,
    "toxicity_category": "骚扰与网络霸凌", // 或 "仇恨言论与身份攻击", "威胁与恐吓", "公开羞辱与诋毁"
    "toxicity_reasons": ["包含攻击性言论", "使用不当词汇"],
    "offensive_elements": ["老东西", "快去死"],
    "target_groups": ["老年人"],
    "severity": "严重", // "轻微", "中等", "严重"
    "emotional_impact": "严重伤害",
    "friendly_alternative": "建议使用更温和的表达方式",
    "explanation_for_elderly": "这段话使用了一些不礼貌的词语...",
    "prevention_tips": ["遇到这类言论时不要回应", "可以举报或屏蔽"]
  },
  "video_id": "7512451849065385274", // 如果是视频内容
  "cached": false // 是否使用了缓存
}
```

### POST `/detect/fake_news`
检测虚假信息

**请求格式**:
```json
{
  "content": "要检测的文本内容或抖音链接",
  "user_id": "用户ID（可选）"
}
```

**响应格式**:
```json
{
  "success": true,
  "message": "检测完成",
  "data": {
    "is_fake_for_elderly": true,
    "confidence": 0.88,
    "fake_news_category": "身份冒充", // 或 "虚假致富经与技能培训", "伪科学养生与健康焦虑", "诱导性消费与直播陷阱", "AI生成式虚假内容"
    "fake_aspects": ["自称知名军医但未提供证明", "声称可以治疗所有疾病"],
    "false_claims": ["可以治疗所有疾病", "有特效药可以通过微信购买"],
    "manipulation_tactics": ["权威身份冒充", "健康焦虑利用"],
    "risk_level": "高风险", // "低风险", "中等风险", "高风险"
    "factual_version": "正规医疗机构和医生不会通过微信销售药物...",
    "truth_explanation": "这个信息是假的，因为它声称可以治疗所有疾病...",
    "safety_tips": ["不要轻信能治百病的'神医'", "生病时应去正规医院"],
    "red_flags": ["要求加微信", "声称包治百病"]
  },
  "video_id": null,
  "cached": false
}
```

### POST `/detect/privacy`
检测隐私泄露

**请求格式**:
```json
{
  "content": "要检测的文本内容或抖音链接",
  "user_id": "用户ID（可选）"
}
```

**响应格式**:
```json
{
  "success": true,
  "message": "检测完成",
  "data": {
    "has_privacy_risk": true,
    "confidence": 1.0,
    "privacy_category": "核心身份与财务信息", // 或 "个人标识与安全验证信息", "实时位置与日常行踪", "个人生活与家庭关系"
    "risk_level": "极高风险", // "低风险", "中等风险", "高风险", "极高风险"
    "risky_information": [
      {
        "type": "银行卡号",
        "content": "6222024512345678",
        "risk_explanation": "直接分享了完整的银行卡号",
        "potential_consequences": ["银行账户可能被盗刷", "资金损失风险"]
      }
    ],
    "safe_version": "我需要办理银行业务，请问应该去哪个网点？",
    "elderly_explanation": "您刚才分享的信息包含了银行卡号和密码...",
    "protection_tips": ["绝不在网上分享银行卡信息", "密码要保密"],
    "fraud_scenarios": ["诈骗分子可能利用这些信息盗刷银行卡"],
    "suggested_changes": [
      {
        "original": "银行卡号是6222024512345678",
        "suggested": "我的银行卡是XX银行的"
      }
    ]
  },
  "video_id": null,
  "cached": false
}
```

---

## 3. 配置管理 API

### POST `/config/parent`
子女端配置检测关注度

**请求格式**:
```json
{
  "config_data": {
    "骚扰与网络霸凌": 5,
    "仇恨言论与身份攻击": 4,
    "威胁与恐吓": 5,
    "公开羞辱与诋毁": 3
  },
  "service_type": "toxic", // "toxic", "fake_news", "privacy", "all"
  "user_id": "parent_user_123"
}
```

**响应格式**:
```json
{
  "success": true,
  "message": "子女端成功配置 toxic 服务的关注度",
  "updated_services": ["toxic_detector"],
  "config_type": "parent"
}
```

### POST `/config/elderly`
老年人端配置检测关注度

**请求格式**:
```json
{
  "config_data": {
    "身份冒充": 3,
    "虚假致富经与技能培训": 4,
    "伪科学养生与健康焦虑": 5,
    "诱导性消费与直播陷阱": 3,
    "AI生成式虚假内容": 4
  },
  "service_type": "fake_news",
  "user_id": "elderly_user_456"
}
```

**响应格式**:
```json
{
  "success": true,
  "message": "老年人端成功配置 fake_news 服务的关注度",
  "updated_services": ["fake_news_detector"],
  "config_type": "elderly"
}
```
---

## 4. 检测报告 API

### POST `/reports/detection`
生成检测报告

**请求格式**:
```json
{
  "user_id": "user_123",
  "report_type": "total", // "total", "toxic", "fake_news", "privacy"
  "limit": 10 // 分析最近多少次记录，可选，默认10
}
```

**总览报告响应格式** (`report_type: "total"`):
```json
{
  "success": true,
  "message": "检测报告生成成功",
  "report_data": {
    "user_id": "user_123",
    "report_type": "total",
    "analysis_period": "最近 10 次检测记录",
    "statistics": {
      "toxic": 2,
      "fake_news": 1,
      "privacy": 3,
      "total": 6
    },
    "percentages": {
      "toxic_percentage": 33.3,
      "fake_news_percentage": 16.7,
      "privacy_percentage": 50.0
    },
    "recent_detections": [
      {
        "video_id": "7512451849065385274",
        "detection_type": "privacy",
        "result": { /* 完整的检测结果 */ },
        "timestamp": 1648786999.123
      }
    ],
    "summary": "经过分析，您的家人在最近的网络活动中遇到了6次安全风险...",
    "analysis": "整体风险程度中等，建议加强对老年人的网络安全教育...",
    "recommendations": [
      "定期与老年人沟通，教导如何识别和应对网络不良言论",
      "提高老年人的媒体素养，教会他们核实信息来源",
      "强化隐私保护意识，指导安全的信息分享方式"
    ],
    "generated_at": "2024-01-20T10:30:00.000Z"
  },
  "user_id": "user_123",
  "report_type": "total"
}
```

**专项报告响应格式** (`report_type: "toxic"/"fake_news"/"privacy"`):
```json
{
  "success": true,
  "message": "检测报告生成成功",
  "report_data": {
    "user_id": "user_123",
    "report_type": "toxic",
    "analysis_period": "最近 10 次检测记录",
    "total_detections": 3,
    "category_statistics": {
      "骚扰与网络霸凌": 2,
      "威胁与恐吓": 1
    },
    "category_percentages": {
      "骚扰与网络霸凌": 66.7,
      "威胁与恐吓": 33.3
    },
    "recent_detections": [
      {
        "video_id": "7512451849065385274",
        "detection_type": "toxic",
        "category": "骚扰与网络霸凌",
        "result": { /* 完整的检测结果 */ },
        "timestamp": 1648786999.123
      }
    ],
    "summary": "您的家人多次接触到毒性内容，其中骚扰与网络霸凌类型最为突出...",
    "analysis": "频繁接触毒性内容可能对心理健康造成影响，建议加强指导和防护措施。",
    "recommendations": [
      "教导老年人识别和应对网络攻击性言论",
      "建议使用内容过滤功能，减少不良内容曝光"
    ],
    "risk_level": "中等风险",
    "generated_at": "2024-01-20T10:30:00.000Z"
  },
  "user_id": "user_123",
  "report_type": "toxic"
}
```

---

## 6. 数据模型说明

### 检测类别定义

#### 毒性内容类别
- `骚扰与网络霸凌`: 网络反复发送不友善、贬低性或侮辱性信息
- `仇恨言论与身份攻击`: 基于身份特征发表歧视性、攻击性言论
- `威胁与恐吓`: 威胁他人人身安全、财产安全或名誉
- `公开羞辱与诋毁`: 恶意公开私人信息或散布谣言破坏名誉

#### 虚假信息类别
- `身份冒充`: 冒充明星、专家等身份进行欺骗
- `虚假致富经与技能培训`: 宣传虚假赚钱方法和无价值培训
- `伪科学养生与健康焦虑`: 发布虚假养生信息推销保健品
- `诱导性消费与直播陷阱`: 通过表演和夸大功效诱导消费
- `AI生成式虚假内容`: 使用AI技术合成虚假权威形象

#### 隐私泄露类别
- `核心身份与财务信息`: 银行账号、密码、社保号等关键信息
- `个人标识与安全验证信息`: 出生日期、地址、电话、安全问题答案
- `实时位置与日常行踪`: 位置打卡、行程计划、GPS数据
- `个人生活与家庭关系`: 家庭成员信息、健康状况、内部矛盾

### 关注度等级
配置中的关注度等级为 1-5：
- `1`: 非常低关注度
- `2`: 低关注度  
- `3`: 中等关注度
- `4`: 高关注度
- `5`: 非常高关注度

---

## 7. 错误处理

所有API在出现错误时会返回以下格式：

```json
{
  "success": false,
  "message": "错误描述信息",
  "detail": "详细错误信息（可选）"
}
```

常见HTTP状态码：
- `200`: 成功
- `400`: 请求参数错误
- `500`: 服务器内部错误

---
