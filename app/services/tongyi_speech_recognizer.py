#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通义听悟语音识别服务
提供类似speech_recognition.recognize_google的接口
"""

import os
import json
import time
import base64
import logging
import tempfile
from typing import Optional, Dict, Any, Union
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException

# 设置日志
logger = logging.getLogger(__name__)

class TongyiSpeechRecognizer:
    """
    通义听悟语音识别服务类
    提供类似speech_recognition库的接口
    """
    
    def __init__(self, access_key_id: str, access_key_secret: str, app_key: str = None, region: str = "cn-shanghai"):
        """
        初始化通义听悟识别器
        
        Args:
            access_key_id: 阿里云Access Key ID
            access_key_secret: 阿里云Access Key Secret
            app_key: 智能语音交互项目的AppKey (用于录音文件识别)
            region: 地域，默认cn-shanghai
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self.region = region
        
        # 初始化客户端
        self.client = AcsClient(access_key_id, access_key_secret, region)
        
        # 录音文件识别配置
        self.domain = f"filetrans.{region}.aliyuncs.com"
        self.api_version = "2018-08-17"
        self.product = "nls-filetrans"
        
        logger.info(f"通义听悟识别器初始化完成，地域: {region}")
    
    def recognize_from_file(self, 
                            audio_file_path: str, 
                            language: str = "zh-CN",
                            timeout: int = 300,
                            enable_words: bool = False,
                            enable_punctuation: bool = True) -> str:
        """
        从音频文件识别语音 (类似recognize_google接口)
        
        Args:
            audio_file_path: 音频文件路径
            language: 语言代码，默认中文
            timeout: 识别超时时间（秒）
            enable_words: 是否返回词级别信息
            enable_punctuation: 是否启用标点符号预测
            
        Returns:
            识别出的文本
            
        Raises:
            Exception: 识别失败时抛出异常
        """
        if not self.app_key:
            raise ValueError("录音文件识别需要设置app_key")
        
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_file_path}")
        
        logger.info(f"开始识别音频文件: {audio_file_path}")
        
        # 首先需要上传文件到OSS或提供可访问的URL
        # 这里假设文件已经可以通过HTTP访问
        # 实际使用时，您可能需要先上传到OSS
        file_url = self._upload_to_oss_or_get_url(audio_file_path)
        
        try:
            # 提交识别任务
            task_id = self._submit_file_transcription_task(
                file_url=file_url,
                language=language,
                enable_words=enable_words,
                enable_punctuation=enable_punctuation
            )
            
            # 轮询获取结果
            result = self._poll_task_result(task_id, timeout)
            
            # 提取文本
            transcript = self._extract_text_from_result(result)
            
            logger.info(f"识别完成，结果长度: {len(transcript)}")
            return transcript
            
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            raise
    
    def recognize_from_audio_data(self, 
                                audio_data: bytes, 
                                sample_rate: int = 16000,
                                language: str = "zh-CN") -> str:
        """
        从音频数据识别语音 (类似recognize_google接口)
        
        Args:
            audio_data: 音频数据（WAV格式）
            sample_rate: 采样率
            language: 语言代码
            
        Returns:
            识别出的文本
        """
        # 将音频数据保存为临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        
        try:
            return self.recognize_from_file(temp_path, language)
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _upload_to_oss_or_get_url(self, file_path: str) -> str:
        """
        上传文件到OSS或获取可访问的URL
        
        注意：这里简化处理，实际使用时需要实现文件上传到OSS的逻辑
        """
        # TODO: 实现文件上传到OSS的逻辑
        # 这里为了演示，假设文件已经在某个可访问的位置
        
        # 如果文件路径是URL，直接返回
        if file_path.startswith(('http://', 'https://')):
            return file_path
        
        # 实际实现中，您需要：
        # 1. 上传文件到OSS
        # 2. 返回OSS文件的公网可访问URL
        
        # 修正：如果不是http/https链接，则认为是本地文件，并转换为file://协议的URL
        # 确保路径是绝对路径
        abs_path = os.path.abspath(file_path)
        file_url = f"file://{abs_path}"
        logger.info(f"将本地文件路径转换为URL: {file_url}")
        return file_url
    
    def _submit_file_transcription_task(self, 
                                      file_url: str,
                                      language: str = "zh-CN",
                                      enable_words: bool = False,
                                      enable_punctuation: bool = True) -> str:
        """
        提交录音文件识别任务
        
        Returns:
            任务ID
        """
        request = CommonRequest()
        request.set_domain(self.domain)
        request.set_version(self.api_version)
        request.set_product(self.product)
        request.set_action_name("SubmitTask")
        request.set_method('POST')
        
        # 构造任务参数
        task_params = {
            "appkey": self.app_key,
            "file_link": file_url,
            "version": "4.0",
            "format": "mp3",  # 显式指定音频格式为mp3
            "sample_rate": 16000, # 明确告知我们已标准化的采样率
            "enable_words": enable_words,
            "enable_punctuation_prediction": enable_punctuation,
            "enable_inverse_text_normalization": True,  # 启用ITN，数字转换
            "enable_sample_rate_adaptive": False,  # 关闭采样率自适应，因为我们已手动标准化
        }
        
        request.add_body_params("Task", json.dumps(task_params))
        
        try:
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            
            if result.get("StatusText") == "SUCCESS":
                task_id = result.get("TaskId")
                logger.info(f"任务提交成功，TaskId: {task_id}")
                return task_id
            else:
                raise Exception(f"任务提交失败: {result}")
                
        except (ClientException, ServerException) as e:
            logger.error(f"提交任务异常: {e}")
            raise
    
    def _poll_task_result(self, task_id: str, timeout: int = 300) -> Dict[str, Any]:
        """
        轮询任务结果
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            
        Returns:
            识别结果
        """
        request = CommonRequest()
        request.set_domain(self.domain)
        request.set_version(self.api_version)
        request.set_product(self.product)
        request.set_action_name("GetTaskResult")
        request.set_method('GET')
        request.add_query_param("TaskId", task_id)
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.client.do_action_with_exception(request)
                result = json.loads(response)
                
                status = result.get("StatusText")
                
                if status == "SUCCESS":
                    logger.info("识别任务完成")
                    return result
                elif status in ["RUNNING", "QUEUEING"]:
                    logger.debug(f"任务状态: {status}，继续等待...")
                    time.sleep(5)  # 等待5秒后重试
                else:
                    raise Exception(f"任务失败，状态: {status}; 结果: {result}")
                    
            except (ClientException, ServerException) as e:
                logger.error(f"查询任务状态异常: {e}")
                raise
        
        raise TimeoutError(f"识别任务超时（{timeout}秒）")
    
    def _extract_text_from_result(self, result: Dict[str, Any]) -> str:
        """
        从识别结果中提取文本
        """
        try:
            sentences = result.get("Result", {}).get("Sentences", [])
            
            if not sentences:
                logger.warning("识别结果为空")
                return ""
            
            # 按时间顺序合并所有句子
            sentences_sorted = sorted(sentences, key=lambda x: x.get("BeginTime", 0))
            
            text_parts = []
            for sentence in sentences_sorted:
                text = sentence.get("Text", "").strip()
                if text:
                    text_parts.append(text)
            
            full_text = "".join(text_parts)
            return full_text
            
        except Exception as e:
            logger.error(f"提取文本失败: {e}")
            raise
    
    def recognize_google_compatible(self, audio_data, language="zh-CN"):
        """
        提供与speech_recognition.recognize_google兼容的接口
        
        Args:
            audio_data: AudioData对象或bytes数据
            language: 语言代码
            
        Returns:
            识别文本
        """
        # 如果是AudioData对象，提取其中的音频数据
        if hasattr(audio_data, 'get_wav_data'):
            wav_data = audio_data.get_wav_data()
            return self.recognize_from_audio_data(wav_data, language=language)
        elif isinstance(audio_data, bytes):
            return self.recognize_from_audio_data(audio_data, language=language)
        else:
            raise ValueError("不支持的音频数据类型")

# 工厂函数，提供简单的创建接口
def create_tongyi_recognizer(access_key_id: str = None, 
                           access_key_secret: str = None, 
                           app_key: str = None) -> TongyiSpeechRecognizer:
    """
    创建通义听悟识别器实例
    
    Args:
        access_key_id: Access Key ID，默认从环境变量获取
        access_key_secret: Access Key Secret，默认从环境变量获取
        app_key: AppKey，默认从环境变量获取
        
    Returns:
        TongyiSpeechRecognizer实例
    """
    # 从环境变量获取配置
    if not access_key_id:
        access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
    if not access_key_secret:
        access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    if not app_key:
        app_key = os.getenv('ALIBABA_CLOUD_APP_KEY')
    
    if not all([access_key_id, access_key_secret]):
        raise ValueError(
            "请设置阿里云Access Key信息\n"
            "可以通过参数传入，或设置环境变量：\n"
            "ALIBABA_CLOUD_ACCESS_KEY_ID\n"
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET\n"
            "ALIBABA_CLOUD_APP_KEY"
        )
    
    return TongyiSpeechRecognizer(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        app_key=app_key
    )

# 示例用法
if __name__ == "__main__":
    # 使用示例
    try:
        # 方式1：从环境变量创建
        recognizer = create_tongyi_recognizer()
        
        # 方式2：直接指定参数
        # recognizer = TongyiSpeechRecognizer(
        #     access_key_id="your_access_key_id",
        #     access_key_secret="your_access_key_secret", 
        #     app_key="your_app_key"
        # )
        
        # 识别音频文件
        # result = recognizer.recognize_from_file("test.wav", language="zh-CN")
        # print(f"识别结果: {result}")
        
        print("通义听悟识别器创建成功！")
        print("使用说明：")
        print("1. 设置环境变量：ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET, ALIBABA_CLOUD_APP_KEY")
        print("2. 调用recognize_from_file()识别音频文件")
        print("3. 调用recognize_google_compatible()提供兼容接口")
        
    except Exception as e:
        print(f"错误: {e}") 