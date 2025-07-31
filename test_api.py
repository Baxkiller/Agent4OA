#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent4OA 内容安全检测服务 API 测试脚本
测试所有新功能：分离式配置管理、详细检测报告、协同工作模式
"""

import requests
import json
import time
from typing import Dict, Any, List

# 配置
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_12345"

# 测试数据
DETECTION_RULES_CATEGORIES = {
    "toxic": [
        "骚扰与网络霸凌",
        "仇恨言论与身份攻击", 
        "威胁与恐吓",
        "公开羞辱与诋毁"
    ],
    "fake_news": [
        "身份冒充",
        "虚假致富经与技能培训",
        "伪科学养生与健康焦虑",
        "诱导性消费与直播陷阱",
        "AI生成式虚假内容"
    ],
    "privacy": [
        "核心身份与财务信息",
        "个人标识与安全验证信息",
        "实时位置与日常行踪",
        "个人生活与家庭关系"
    ]
}

def test_service_info():
    """测试服务基本信息"""
    print("=" * 60)
    print("测试 1: 服务基本信息")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 服务信息获取成功")
            print(f"服务名称: {data.get('service')}")
            print(f"版本: {data.get('version')}")
            print(f"可用端点: {list(data.get('endpoints', {}).keys())}")
            return True
        else:
            print(f"❌ 服务信息获取失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_parent_config_api():
    """测试子女端配置API"""
    print("\n" + "=" * 60)
    print("测试 2: 子女端配置API")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "子女配置毒性内容检测",
            "data": {
                "config_data": {
                    "骚扰与网络霸凌": 5,
                    "仇恨言论与身份攻击": 4,
                    "威胁与恐吓": 5,
                    "公开羞辱与诋毁": 3
                },
                "service_type": "toxic",
                "user_id": TEST_USER_ID
            }
        },
        {
            "name": "子女配置虚假信息检测",
            "data": {
                "config_data": {
                    "身份冒充": 5,
                    "虚假致富经与技能培训": 4,
                    "伪科学养生与健康焦虑": 5,
                    "诱导性消费与直播陷阱": 4,
                    "AI生成式虚假内容": 3
                },
                "service_type": "fake_news",
                "user_id": TEST_USER_ID
            }
        },
        {
            "name": "子女配置隐私保护检测",
            "data": {
                "config_data": {
                    "核心身份与财务信息": 5,
                    "个人标识与安全验证信息": 4,
                    "实时位置与日常行踪": 3,
                    "个人生活与家庭关系": 3
                },
                "service_type": "privacy",
                "user_id": TEST_USER_ID
            }
        },
        {
            "name": "子女配置所有服务",
            "data": {
                "config_data": {
                    "骚扰与网络霸凌": 4,
                    "身份冒充": 5,
                    "核心身份与财务信息": 5
                },
                "service_type": "all",
                "user_id": TEST_USER_ID
            }
        },
        {
            "name": "错误的服务类型",
            "data": {
                "config_data": {"test": 3},
                "service_type": "invalid_type",
                "user_id": TEST_USER_ID
            },
            "should_fail": True
        }
    ]
    
    success_count = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 2.{i}: {case['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(
                f"{BASE_URL}/config/parent",
                json=case["data"],
                headers={"Content-Type": "application/json"}
            )
            
            print(f"状态码: {response.status_code}")
            result = response.json()
            
            should_fail = case.get("should_fail", False)
            
            if should_fail:
                if response.status_code != 200 or not result.get("success", True):
                    print("✅ 预期的错误处理正确")
                    success_count += 1
                else:
                    print("❌ 应该失败但成功了")
            else:
                if response.status_code == 200 and result.get("success"):
                    print("✅ 子女配置成功")
                    print(f"更新的服务: {result.get('updated_services', [])}")
                    print(f"配置类型: {result.get('config_type')}")
                    success_count += 1
                else:
                    print(f"❌ 配置失败: {result.get('message', '未知错误')}")
        
        except Exception as e:
            print(f"❌ 请求异常: {e}")
    
    print(f"\n子女端配置测试结果: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)

def test_elderly_config_api():
    """测试老年人端配置API"""
    print("\n" + "=" * 60)
    print("测试 3: 老年人端配置API")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "老年人配置毒性内容检测",
            "data": {
                "config_data": {
                    "骚扰与网络霸凌": 2,
                    "仇恨言论与身份攻击": 3,
                    "威胁与恐吓": 4,
                    "公开羞辱与诋毁": 2
                },
                "service_type": "toxic",
                "user_id": TEST_USER_ID
            }
        },
        {
            "name": "老年人配置虚假信息检测",
            "data": {
                "config_data": {
                    "身份冒充": 3,
                    "虚假致富经与技能培训": 2,
                    "伪科学养生与健康焦虑": 4,
                    "诱导性消费与直播陷阱": 3,
                    "AI生成式虚假内容": 2
                },
                "service_type": "fake_news",
                "user_id": TEST_USER_ID
            }
        },
        {
            "name": "老年人配置所有服务",
            "data": {
                "config_data": {
                    "骚扰与网络霸凌": 3,
                    "身份冒充": 3,
                    "核心身份与财务信息": 4
                },
                "service_type": "all",
                "user_id": TEST_USER_ID
            }
        }
    ]
    
    success_count = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 3.{i}: {case['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(
                f"{BASE_URL}/config/elderly",
                json=case["data"],
                headers={"Content-Type": "application/json"}
            )
            
            print(f"状态码: {response.status_code}")
            result = response.json()
            
            if response.status_code == 200 and result.get("success"):
                print("✅ 老年人配置成功")
                print(f"更新的服务: {result.get('updated_services', [])}")
                print(f"配置类型: {result.get('config_type')}")
                success_count += 1
            else:
                print(f"❌ 配置失败: {result.get('message', '未知错误')}")
        
        except Exception as e:
            print(f"❌ 请求异常: {e}")
    
    print(f"\n老年人端配置测试结果: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)

def test_detection_apis():
    """测试检测API"""
    print("\n" + "=" * 60)
    print("测试 4: 内容检测API")
    print("=" * 60)
    
    test_contents = [
        {
            "content": "你个老东西，活着浪费粮食，快去死吧！",
            "type": "toxic",
            "description": "毒性内容测试"
        },
        {
            "content": "我是知名军医，可以治疗所有疾病，需要的话加我微信购买特效药。",
            "type": "fake_news", 
            "description": "虚假信息测试"
        },
        {
            "content": "我的银行卡号是6222024512345678，密码是123456，家住北京市朝阳区某某小区。",
            "type": "privacy",
            "description": "隐私泄露测试"
        }
    ]
    
    success_count = 0
    
    for i, test in enumerate(test_contents, 1):
        print(f"\n测试用例 4.{i}: {test['description']}")
        print("-" * 40)
        print(f"测试内容: {test['content'][:50]}...")
        
        try:
            response = requests.post(
                f"{BASE_URL}/detect/{test['type']}",
                json={
                    "content": test["content"],
                    "user_id": TEST_USER_ID
                },
                headers={"Content-Type": "application/json"}
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✅ 检测成功")
                    data = result.get("data", {})
                    
                    if test["type"] == "toxic":
                        print(f"检测到毒性: {data.get('is_toxic_for_elderly', False)}")
                        print(f"毒性类别: {data.get('toxicity_category', '未知')}")
                    elif test["type"] == "fake_news":
                        print(f"检测到虚假: {data.get('is_fake_for_elderly', False)}")
                        print(f"虚假类别: {data.get('fake_news_category', '未知')}")
                    elif test["type"] == "privacy":
                        print(f"检测到隐私风险: {data.get('has_privacy_risk', False)}")
                        print(f"隐私类别: {data.get('privacy_category', '未知')}")
                    
                    success_count += 1
                else:
                    print(f"❌ 检测失败: {result.get('message', '未知错误')}")
            else:
                print(f"❌ 请求失败: {response.text}")
        
        except Exception as e:
            print(f"❌ 请求异常: {e}")
        
        # 添加延迟避免API限流
        time.sleep(1)
    
    print(f"\n检测API测试结果: {success_count}/{len(test_contents)} 通过")
    return success_count == len(test_contents)

def test_detection_reports_api():
    """测试检测报告API"""
    print("\n" + "=" * 60)
    print("测试 5: 检测报告API")
    print("=" * 60)
    
    report_types = [
        {
            "type": "total",
            "description": "总览报告"
        },
        {
            "type": "toxic",
            "description": "毒性内容专项报告"
        },
        {
            "type": "fake_news",
            "description": "虚假信息专项报告"
        },
        {
            "type": "privacy",
            "description": "隐私保护专项报告"
        },
        {
            "type": "invalid",
            "description": "无效报告类型",
            "should_fail": True
        }
    ]
    
    success_count = 0
    
    for i, report in enumerate(report_types, 1):
        print(f"\n测试用例 5.{i}: {report['description']}")
        print("-" * 40)
        
        try:
            response = requests.post(
                f"{BASE_URL}/reports/detection",
                json={
                    "user_id": TEST_USER_ID,
                    "report_type": report["type"],
                    "limit": 5
                },
                headers={"Content-Type": "application/json"}
            )
            
            print(f"状态码: {response.status_code}")
            result = response.json()
            
            should_fail = report.get("should_fail", False)
            
            if should_fail:
                if not result.get("success"):
                    print("✅ 预期的错误处理正确")
                    success_count += 1
                else:
                    print("❌ 应该失败但成功了")
            else:
                if response.status_code == 200 and result.get("success"):
                    print("✅ 报告生成成功")
                    report_data = result.get("report_data", {})
                    print(f"报告类型: {report_data.get('report_type', '未知')}")
                    
                    if report["type"] == "total":
                        statistics = report_data.get("statistics", {})
                        print(f"总检测次数: {statistics.get('total', 0)}")
                        print(f"毒性内容: {statistics.get('toxic', 0)}")
                        print(f"虚假信息: {statistics.get('fake_news', 0)}")
                        print(f"隐私风险: {statistics.get('privacy', 0)}")
                    else:
                        print(f"检测总数: {report_data.get('total_detections', 0)}")
                        print(f"类别统计: {report_data.get('category_statistics', {})}")
                    
                    print(f"风险等级: {report_data.get('risk_level', '未知')}")
                    print(f"建议数量: {len(report_data.get('recommendations', []))}")
                    success_count += 1
                else:
                    print(f"❌ 报告生成失败: {result.get('message', '未知错误')}")
        
        except Exception as e:
            print(f"❌ 请求异常: {e}")
    
    print(f"\n检测报告测试结果: {success_count}/{len(report_types)} 通过")
    return success_count == len(report_types)

def test_cache_status_api():
    """测试缓存状态API"""
    print("\n" + "=" * 60)
    print("测试 6: 缓存状态API")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/cache/status")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 缓存状态获取成功")
            print(f"内存缓存大小: {data.get('memory_cache_size', 0)}")
            print(f"文件缓存视频数: {data.get('file_cache_videos', 0)}")
            print(f"缓存键数量: {len(data.get('cache_keys', []))}")
            return True
        else:
            print(f"❌ 缓存状态获取失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_legacy_config_api():
    """测试兼容性配置API"""
    print("\n" + "=" * 60)
    print("测试 7: 兼容性配置API (旧版)")
    print("=" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/config/prompts",
            json={
                "parent_json": {
                    "骚扰与网络霸凌": 4,
                    "身份冒充": 5
                },
                "child_json": {
                    "骚扰与网络霸凌": 3,
                    "身份冒充": 2
                },
                "service_type": "all"
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 兼容性配置成功")
                print(f"更新的服务: {result.get('updated_services', [])}")
                return True
            else:
                print(f"❌ 配置失败: {result.get('message', '未知错误')}")
                return False
        else:
            print(f"❌ 请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def run_comprehensive_tests():
    """运行完整的测试套件"""
    print("🚀 开始运行 Agent4OA 内容安全检测服务完整测试")
    print("=" * 80)
    
    test_results = []
    
    # 执行所有测试
    tests = [
        ("服务基本信息", test_service_info),
        ("子女端配置API", test_parent_config_api),
        ("老年人端配置API", test_elderly_config_api),
        ("内容检测API", test_detection_apis),
        ("检测报告API", test_detection_reports_api),
        ("缓存状态API", test_cache_status_api),
        ("兼容性配置API", test_legacy_config_api)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 执行异常: {e}")
            test_results.append((test_name, False))
    
    # 显示测试结果摘要
    print("\n" + "=" * 80)
    print("🏁 测试结果摘要")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<25} : {status}")
        if result:
            passed += 1
    
    print("-" * 80)
    print(f"总体结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统功能正常")
        print("\n📋 功能验证完成:")
        print("• 分离式配置管理 - 子女和老年人独立配置")
        print("• 详细检测报告 - 支持总览和分类报告")
        print("• 协同工作模式 - 综合双方配置进行检测")
        print("• 向后兼容性 - 保持旧版API兼容")
        print("• 专业分析内容 - 面向子女的详细建议")
    else:
        print(f"⚠️  {total - passed} 个测试失败，需要检查相关功能")
    
    return passed == total

if __name__ == "__main__":
    run_comprehensive_tests() 