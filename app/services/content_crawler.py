import os
import requests
import re
import json
import tempfile
import subprocess
from typing import List, Optional, Tuple, Dict
from urllib.parse import urlparse
import speech_recognition as sr
from pydub import AudioSegment
import logging
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

# 导入通义听悟语音识别
try:
    from .tongyi_speech_recognizer import create_tongyi_recognizer
    TONGYI_AVAILABLE = True
except ImportError:
    TONGYI_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContentCrawler:
    """内容爬取服务 - 专注于给定URL的内容爬取和存储"""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        初始化爬虫
        
        Args:
            cache_dir: 缓存目录
        """
        self.recognizer = sr.Recognizer()
        self.session = requests.Session()
        self.cache_dir = cache_dir
        
        # 初始化通义听悟识别器
        self.tongyi_recognizer = None
        if TONGYI_AVAILABLE:
            try:
                self.tongyi_recognizer = create_tongyi_recognizer()
                logger.info("✅ 通义听悟语音识别器初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ 通义听悟初始化失败，将使用备用方案: {e}")
        else:
            logger.info("ℹ️ 通义听悟未安装，使用传统语音识别")
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
        
        # 设置请求头，与参考文件完全一致
        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
            'referer': 'https://www.douyin.com/?is_from_mobile_home=1&recommend=1'
        })
        
        logger.info("ContentCrawler初始化完成")
    
    def check_cache(self, video_id: str) -> Optional[dict]:
        """
        检查本地缓存是否存在
        
        Args:
            video_id: 视频ID
            
        Returns:
            缓存的结果字典，如果不存在返回None
        """
        cache_path = os.path.join(self.cache_dir, video_id)
        result_file = os.path.join(cache_path, "result.json")
        
        if os.path.exists(result_file):
            logger.info(f"发现缓存: {video_id}")
            
            with open(result_file, 'r', encoding='utf-8') as f:
                cached_result = json.load(f)
            
            # 验证缓存文件是否完整
            if self._validate_cache(cache_path, cached_result):
                logger.info(f"使用缓存结果: {video_id}")
                # 更新路径为当前缓存路径
                cached_result = self._update_cache_paths(cached_result, cache_path)
                return cached_result
            else:
                logger.warning(f"缓存不完整，将重新处理: {video_id}")
                
        return None
    
    def _validate_cache(self, cache_path: str, result: dict) -> bool:
        """验证缓存文件是否完整"""
        # 检查必要文件是否存在
        if result.get('cover_path'):
            if not os.path.exists(os.path.join(cache_path, "cover.jpg")):
                return False
        
        if result.get('frames'):
            for i in range(len(result['frames'])):
                frame_file = f"frame_{i+1:03d}.jpg"
                if not os.path.exists(os.path.join(cache_path, frame_file)):
                    return False
        
        if result.get('images'):
            for i in range(len(result['images'])):
                img_file = f"image_{i+1:03d}.jpg"
                if not os.path.exists(os.path.join(cache_path, img_file)):
                    return False
        
        # 检查音频/视频文件
        media_files = ['media.m4a', 'video.m4a', 'video.mp4', 'audio.mp3']
        has_media = any(os.path.exists(os.path.join(cache_path, f)) for f in media_files)
        
        if result.get('media_type') in ['video', 'audio'] and not has_media:
            return False
        
        return True
    
    def _update_cache_paths(self, result: dict, cache_path: str) -> dict:
        """更新缓存结果中的文件路径"""
        updated_result = result.copy()
        
        # 更新封面路径
        if result.get('cover_path'):
            updated_result['cover_path'] = os.path.join(cache_path, "cover.jpg")
        
        # 更新帧路径
        if result.get('frames'):
            updated_frames = []
            for i in range(len(result['frames'])):
                frame_file = f"frame_{i+1:03d}.jpg"
                updated_frames.append(os.path.join(cache_path, frame_file))
            updated_result['frames'] = updated_frames
        
        # 更新图片路径
        if result.get('images'):
            updated_images = []
            for i in range(len(result['images'])):
                img_file = f"image_{i+1:03d}.jpg"
                updated_images.append(os.path.join(cache_path, img_file))
            updated_result['images'] = updated_images
        
        # 更新音频/视频路径
        if result.get('video_path'):
            video_files = ['media.m4a', 'video.m4a', 'video.mp4']
            for filename in video_files:
                file_path = os.path.join(cache_path, filename)
                if os.path.exists(file_path):
                    updated_result['video_path'] = file_path
                    break
        
        if result.get('audio_path'):
            audio_files = ['audio.mp3', 'media.wav', 'video.wav']
            for filename in audio_files:
                file_path = os.path.join(cache_path, filename)
                if os.path.exists(file_path):
                    updated_result['audio_path'] = file_path
                    break
        
        return updated_result
    
    def save_cache(self, video_id: str, result: dict) -> None:
        """
        保存结果到缓存
        
        Args:
            video_id: 视频ID
            result: 处理结果
        """
        try:
            cache_path = os.path.join(self.cache_dir, video_id)
            result_file = os.path.join(cache_path, "result.json")
            
            # 创建相对路径的结果副本用于保存
            cache_result = result.copy()
            
            # 转换为相对路径
            if result.get('cover_path'):
                cache_result['cover_path'] = "cover.jpg"
            
            if result.get('frames'):
                cache_result['frames'] = [f"frame_{i+1:03d}.jpg" for i in range(len(result['frames']))]
            
            if result.get('images'):
                cache_result['images'] = [f"image_{i+1:03d}.jpg" for i in range(len(result['images']))]
            
            if result.get('video_path'):
                cache_result['video_path'] = os.path.basename(result['video_path'])
            
            if result.get('audio_path'):
                cache_result['audio_path'] = os.path.basename(result['audio_path'])
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(cache_result, f, ensure_ascii=False, indent=2)
                
            logger.info(f"缓存已保存: {video_id}")
            
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def extract_video_info(self, video_url: str) -> Dict:
        """
        从抖音页面提取视频信息
        
        Args:
            video_url: 抖音视频链接
            
        Returns:
            包含视频信息的字典
        """
        try:
            logger.info(f"开始提取视频信息: {video_url}")
            
            # 获取页面内容
            response = self.session.get(video_url, timeout=15)
            response.raise_for_status()
            
            # 提取页面中的JSON数据
            html_content = response.text
            
            # 查找_ROUTER_DATA - 使用更宽松的正则表达式
            router_data_match = re.search(r'_ROUTER_DATA\s*=\s*(\{.*?\});', html_content, re.DOTALL)
            
            if not router_data_match:
                # 尝试其他可能的格式
                router_data_match = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\});', html_content, re.DOTALL)
            
            if not router_data_match:
                logger.error("未找到_ROUTER_DATA")
                logger.debug(f"页面内容长度: {len(html_content)}")
                # 保存页面内容用于调试
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.debug("页面内容已保存到 debug_page.html")
                return {}
            
            json_data_str = router_data_match.group(1)
            logger.info(f"提取到JSON数据长度: {len(json_data_str)}")
            
            # 解析JSON数据，处理可能的转义字符
            try:
                json_data = json.loads(json_data_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                # 尝试处理转义字符
                json_data_str = json_data_str.replace('\\u002F', '/')
                json_data = json.loads(json_data_str)
            
            # 提取视频信息
            try:
                item_list = json_data['loaderData']['video_(id)/page']['videoInfoRes']['item_list'][0]
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"JSON数据结构异常: {e}")
                logger.debug(f"JSON结构: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
                return {}
            
            # 解析视频信息
            video_info = {
                'aweme_id': item_list.get('aweme_id', ''),
                'title': item_list.get('desc', ''),
                'nickname': item_list.get('author', {}).get('nickname', ''),
                'video_url': '',
                'audio_url': '',
                'cover_url': '',
                'images': []
            }
            
            # 获取视频/音频URL
            video_data = item_list.get('video', {})
            if video_data:
                play_addr = video_data.get('play_addr', {})
                uri = play_addr.get('uri', '')
                
                if uri:
                    if 'mp3' in uri:
                        video_info['audio_url'] = uri
                    else:
                        video_info['video_url'] = f'https://www.douyin.com/aweme/v1/play/?video_id={uri}'
                        # 尝试获取音频URL
                        audio_uri = video_data.get('audio_addr', {}).get('uri', '')
                        if audio_uri:
                            video_info['audio_url'] = audio_uri
                
                # 获取封面
                cover_data = video_data.get('cover', {})
                if cover_data and cover_data.get('url_list'):
                    video_info['cover_url'] = cover_data['url_list'][0]
            
            # 获取图集图片（如果有）
            images = item_list.get('images', [])
            if images:
                video_info['images'] = [img['url_list'][0] for img in images if img.get('url_list')]
            
            logger.info(f"成功提取视频信息: {video_info['title']}")
            logger.info(f"图片数量: {len(video_info['images'])}")
            logger.info(f"音频URL: {'是' if video_info['audio_url'] else '否'}")
            
            return video_info
            
        except Exception as e:
            logger.error(f"提取视频信息失败: {e}")
            return {}
    
    def download_file(self, url: str, output_path: str) -> bool:
        """
        下载文件到指定路径
        
        Args:
            url: 文件URL
            output_path: 输出路径
            
        Returns:
            下载是否成功
        """
        try:
            logger.info(f"开始下载文件: {url}")
            
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(output_path)
            logger.info(f"文件下载成功: {output_path} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return False
    
    def download_images(self, image_urls: List[str], output_dir: str) -> List[str]:
        """
        下载图片文件
        
        Args:
            image_urls: 图片URL列表
            output_dir: 输出目录
            
        Returns:
            成功下载的图片文件路径列表
        """
        downloaded_images = []
        
        if not image_urls:
            logger.info("没有图片需要下载")
            return downloaded_images
        
        logger.info(f"开始下载 {len(image_urls)} 张图片")
        
        for i, img_url in enumerate(image_urls):
            try:
                # 生成文件名
                img_filename = f"image_{i+1:03d}.jpg"
                img_path = os.path.join(output_dir, img_filename)
                
                if self.download_file(img_url, img_path):
                    downloaded_images.append(img_path)
                else:
                    logger.warning(f"图片下载失败: {img_url}")
                    
            except Exception as e:
                logger.error(f"下载图片 {i+1} 失败: {e}")
        
        logger.info(f"图片下载完成: {len(downloaded_images)}/{len(image_urls)}")
        return downloaded_images
    
    def download_audio(self, audio_url: str, output_dir: str) -> str:
        """
        下载音频文件
        
        Args:
            audio_url: 音频URL
            output_dir: 输出目录
            
        Returns:
            下载的音频文件路径，失败返回空字符串
        """
        if not audio_url:
            logger.info("没有音频URL")
            return ""
        
        try:
            # 确定文件扩展名
            if audio_url.endswith('.mp3') or 'mp3' in audio_url:
                audio_filename = "audio.mp3"
            else:
                audio_filename = "audio.m4a"  # 抖音通常使用m4a格式
            
            audio_path = os.path.join(output_dir, audio_filename)
            
            if self.download_file(audio_url, audio_path):
                return audio_path
            else:
                logger.error("音频下载失败")
                return ""
                
        except Exception as e:
            logger.error(f"下载音频失败: {e}")
            return ""
    
    def transcribe_audio(self, audio_path: str) -> str:
        """
        将音频文件转换为文字
        优先使用通义听悟，失败时降级到其他方案
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            转录文本
        """
        try:
            transcript = ""
            
            # 检查文件是否存在
            if not os.path.exists(audio_path):
                logger.error(f"音频文件不存在: {audio_path}")
                return ""
            
            logger.info(f"开始语音识别: {os.path.basename(audio_path)}")
            
            # 方案1: 优先使用通义听悟 🎯
            if self.tongyi_recognizer:
                try:
                    logger.info("🔥 尝试通义听悟识别...")
                    
                    # 上传文件并识别（这里需要实现OSS上传逻辑）
                    # 为了演示，我们先使用本地文件识别的方式
                    transcript = self._tongyi_recognize_local_file(audio_path)
                    
                    if transcript and len(transcript.strip()) > 0:
                        logger.info(f"✅ 通义听悟识别成功: {len(transcript)} 字符")
                        return transcript
                    else:
                        logger.warning("⚠️ 通义听悟返回空结果，尝试其他方案")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 通义听悟识别失败: {e}，尝试其他方案")
            
            # 方案2: 使用OpenAI Whisper (如果可用)
            transcript = self._try_openai_whisper(audio_path)
            if transcript:
                return transcript
            
            # 方案3: 使用Vosk离线识别 (如果可用)
            transcript = self._try_vosk_recognition(audio_path)
            if transcript:
                return transcript
            
            # 方案4: 使用百度语音识别 (如果可用)
            transcript = self._try_baidu_recognition(audio_path)
            if transcript:
                return transcript
            
            # 方案5: 最后使用Google API (传统方案)
            transcript = self._try_google_recognition(audio_path)
            if transcript:
                return transcript
            
            logger.warning("❌ 所有语音识别方法都失败了")
            return ""
            
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            return ""
    
    def _tongyi_recognize_local_file(self, audio_path: str) -> str:
        """使用通义听悟识别本地文件"""
        try:
            # 检查文件格式，通义听悟支持多种格式
            supported_formats = ['.wav', '.mp3', '.m4a', '.mp4', '.aac', '.flac']
            file_ext = os.path.splitext(audio_path)[1].lower()
            
            if file_ext not in supported_formats:
                logger.info(f"转换音频格式 {file_ext} -> .wav")
                audio_path = self._convert_audio_format(audio_path)
            
            # 这里需要实现实际的文件上传到OSS或使用URL的逻辑
            # 目前作为占位符，实际使用时需要根据你的OSS配置实现
            
            # TODO: 实现OSS上传逻辑
            # file_url = self._upload_to_oss(audio_path)
            # return self.tongyi_recognizer.recognize_from_file(file_url, language="zh-CN")
            
            # 临时方案：如果文件已经是URL格式，直接使用
            if audio_path.startswith(('http://', 'https://')):
                return self.tongyi_recognizer.recognize_from_file(audio_path, language="zh-CN")
            
            # 如果是本地文件，暂时跳过通义听悟
            logger.info("通义听悟需要文件URL，跳过本地文件识别")
            return ""
            
        except Exception as e:
            logger.error(f"通义听悟识别异常: {e}")
            return ""
    
    def _try_openai_whisper(self, audio_path: str) -> str:
        """尝试使用OpenAI Whisper识别"""
        try:
            import openai
            
            # 检查API密钥
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == 'your_openai_api_key_here':
                return ""
            
            logger.info("🌟 尝试OpenAI Whisper识别...")
            
            # 读取音频文件
            with open(audio_path, 'rb') as audio_file:
                client = openai.OpenAI(api_key=api_key)
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="zh"
                )
                
                result_text = transcript.text.strip()
                if result_text:
                    logger.info(f"✅ OpenAI Whisper识别成功: {len(result_text)} 字符")
                    return result_text
                    
        except ImportError:
            logger.debug("OpenAI库未安装")
        except Exception as e:
            logger.warning(f"OpenAI Whisper识别失败: {e}")
        
        return ""
    
    def _try_vosk_recognition(self, audio_path: str) -> str:
        """尝试使用Vosk离线识别"""
        try:
            import vosk
            import wave
            import json
            
            logger.info("🌟 尝试Vosk离线识别...")
            
            # 检查模型是否存在
            model_path = "models/vosk-model-cn"
            if not os.path.exists(model_path):
                logger.debug("Vosk中文模型不存在")
                return ""
            
            # 转换为WAV格式
            wav_path = self._convert_audio_format(audio_path, target_format='wav')
            
            # 初始化模型和识别器
            model = vosk.Model(model_path)
            rec = vosk.KaldiRecognizer(model, 16000)
            
            # 读取音频文件
            wf = wave.open(wav_path, 'rb')
            
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                    
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if result.get('text'):
                        results.append(result['text'])
            
            # 获取最后的结果
            final_result = json.loads(rec.FinalResult())
            if final_result.get('text'):
                results.append(final_result['text'])
            
            wf.close()
            
            full_text = ' '.join(results).strip()
            if full_text:
                logger.info(f"✅ Vosk识别成功: {len(full_text)} 字符")
                return full_text
                
        except ImportError:
            logger.debug("Vosk库未安装")
        except Exception as e:
            logger.warning(f"Vosk识别失败: {e}")
        
        return ""
    
    def _try_baidu_recognition(self, audio_path: str) -> str:
        """尝试使用百度语音识别"""
        try:
            from aip import AipSpeech
            
            logger.info("🌟 尝试百度语音识别...")
            
            # 检查百度API配置
            app_id = os.getenv('BAIDU_APP_ID')
            api_key = os.getenv('BAIDU_API_KEY') 
            secret_key = os.getenv('BAIDU_SECRET_KEY')
            
            if not all([app_id, api_key, secret_key]):
                return ""
            
            # 初始化百度客户端
            client = AipSpeech(app_id, api_key, secret_key)
            
            # 转换为PCM格式
            pcm_path = self._convert_audio_format(audio_path, target_format='pcm')
            
            # 读取音频文件
            with open(pcm_path, 'rb') as fp:
                audio_data = fp.read()
            
            # 语音识别
            result = client.asr(audio_data, 'pcm', 16000, {'dev_pid': 1537})
            
            if result.get('err_no') == 0:
                text = ''.join(result.get('result', []))
                if text:
                    logger.info(f"✅ 百度识别成功: {len(text)} 字符")
                    return text
                    
        except ImportError:
            logger.debug("百度AIP库未安装")
        except Exception as e:
            logger.warning(f"百度语音识别失败: {e}")
        
        return ""
    
    def _try_google_recognition(self, audio_path: str) -> str:
        """尝试使用Google语音识别 (传统方案)"""
        try:
            logger.info("🌟 尝试Google语音识别...")
            
            # 转换为WAV格式
            wav_path = self._convert_audio_format(audio_path, target_format='wav')
            
            with sr.AudioFile(wav_path) as source:
                # 调整环境噪音
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = self.recognizer.record(source)
                
                # 尝试多种语言
                languages = ['zh-CN', 'en-US']
                
                for lang in languages:
                    try:
                        logger.info(f"尝试Google识别 ({lang})...")
                        transcript = self.recognizer.recognize_google(audio_data, language=lang)
                        if transcript:
                            logger.info(f"✅ Google识别成功 ({lang}): {len(transcript)} 字符")
                            return transcript
                    except sr.UnknownValueError:
                        logger.debug(f"Google API无法识别语音内容 ({lang})")
                        continue
                    except sr.RequestError as e:
                        logger.warning(f"Google API请求失败 ({lang}): {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"Google语音识别失败: {e}")
        
        return ""
    
    def _convert_audio_format(self, audio_path: str, target_format: str = 'wav') -> str:
        """转换音频格式"""
        try:
            if target_format == 'wav':
                output_path = audio_path.rsplit('.', 1)[0] + '.wav'
            elif target_format == 'pcm':
                output_path = audio_path.rsplit('.', 1)[0] + '.pcm'
            else:
                return audio_path
            
            # 如果已经是目标格式，直接返回
            if audio_path.endswith(f'.{target_format}'):
                return audio_path
            
            # 如果转换后的文件已存在，直接返回
            if os.path.exists(output_path):
                return output_path
            
            logger.info(f"转换音频格式: {os.path.basename(audio_path)} -> {target_format.upper()}")
            
            # 使用pydub转换
            if audio_path.endswith('.mp3'):
                audio = AudioSegment.from_mp3(audio_path)
            elif audio_path.endswith('.m4a'):
                audio = AudioSegment.from_file(audio_path, format="m4a")
            elif audio_path.endswith('.mp4'):
                audio = AudioSegment.from_file(audio_path, format="mp4")
            else:
                audio = AudioSegment.from_file(audio_path)
            
            if target_format == 'wav':
                audio.export(output_path, format="wav")
            elif target_format == 'pcm':
                # 转为16kHz, 16bit, 单声道PCM
                audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                audio.export(output_path, format="wav")
                
                # 提取PCM数据
                import wave
                with wave.open(output_path, 'rb') as wav_file:
                    frames = wav_file.readframes(wav_file.getnframes())
                
                with open(output_path.replace('.wav', '.pcm'), 'wb') as pcm_file:
                    pcm_file.write(frames)
                
                output_path = output_path.replace('.wav', '.pcm')
            
            logger.info(f"音频格式转换完成: {os.path.basename(output_path)}")
            return output_path
            
        except Exception as e:
            logger.error(f"音频格式转换失败: {e}")
            return audio_path
    
    def extract_frames_from_video(self, video_path: str, output_dir: str, max_frames: int = 5) -> List[str]:
        """
        从视频文件中提取帧
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            max_frames: 最大提取帧数
            
        Returns:
            提取的帧文件路径列表
        """
        frame_paths = []
        
        try:
            logger.info(f"开始从视频提取帧: {video_path}")
            
            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                logger.error("无法打开视频文件")
                return frame_paths
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"视频信息: {total_frames} 帧, {fps:.1f} FPS, {duration:.1f} 秒")
            
            # 计算提取间隔
            if total_frames <= max_frames:
                frame_indices = list(range(total_frames))
            else:
                frame_indices = [int(i * total_frames / max_frames) for i in range(max_frames)]
            
            # 提取帧
            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    frame_filename = f"frame_{i+1:03d}.jpg"
                    frame_path = os.path.join(output_dir, frame_filename)
                    
                    # 保存帧
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                    logger.info(f"提取帧 {i+1}: {frame_filename}")
            
            cap.release()
            logger.info(f"视频帧提取完成: {len(frame_paths)} 帧")
            
        except Exception as e:
            logger.error(f"视频帧提取失败: {e}")
        
        return frame_paths

    def download_media(self, media_url: str, output_dir: str) -> Tuple[str, str]:
        """
        下载媒体文件，自动判断是视频还是音频
        
        Args:
            media_url: 媒体URL
            output_dir: 输出目录
            
        Returns:
            (文件路径, 文件类型) - 类型为 'video' 或 'audio'
        """
        if not media_url:
            return "", ""
        
        try:
            logger.info(f"开始下载媒体: {media_url}")
            
            # 判断文件类型
            if any(ext in media_url.lower() for ext in ['.mp4', '.m4v', '.avi', '.mov', '.m4a']):
                if '.m4a' in media_url.lower():
                    media_type = "video"  # m4a通常包含视频
                    filename = "video.m4a"
                else:
                    media_type = "video"
                    filename = "video.mp4"
            elif any(ext in media_url.lower() for ext in ['.mp3', '.wav', '.aac']):
                media_type = "audio"
                filename = "audio.mp3"
            else:
                # 默认尝试作为视频
                media_type = "video"
                filename = "media.m4a"
            
            media_path = os.path.join(output_dir, filename)
            
            if self.download_file(media_url, media_path):
                return media_path, media_type
            else:
                return "", ""
                
        except Exception as e:
            logger.error(f"下载媒体失败: {e}")
            return "", ""

    def process_douyin_content(self, resolved_url: str, output_dir: str = None) -> dict:
        """
        处理抖音内容的完整流程 (接收已解析的URL)
        
        Args:
            resolved_url: 已解析的抖音视频链接
            output_dir: 输出目录，如果不指定则使用缓存目录
            
        Returns:
            处理结果字典，同时保存到本地JSON文件
        """
        result = {
            'success': False,
            'video_url': '',
            'video_info': {},
            'media_type': '',
            'cover_path': '',
            'images': [],
            'frames': [],
            'audio_path': '',
            'video_path': '',
            'transcript': '',
            'error': '',
            'from_cache': False
        }
        
        try:
            logger.info(f"开始处理抖音内容: {resolved_url}")
            
            result['video_url'] = resolved_url
            
            # 1. 提取视频信息
            video_info = self.extract_video_info(resolved_url)
            
            if not video_info:
                result['error'] = "无法提取视频信息"
                return result
                
            result['video_info'] = video_info
            
            # 2. 提取视频ID
            video_id = video_info.get('aweme_id', '')
            if not video_id:
                # 尝试从URL提取
                video_id_match = re.search(r'/video/(\d+)', resolved_url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                else:
                    video_id = f"unknown_{int(time.time())}"
            
            logger.info(f"视频ID: {video_id}")
            
            # 3. 检查缓存
            cached_result = self.check_cache(video_id)
            if cached_result:
                result = cached_result
                result['from_cache'] = True
                logger.info("使用缓存结果")
                # 保存到指定输出目录的JSON文件
                self._save_result_json(result, output_dir, video_id)
                return result
            
            # 4. 确定输出目录
            if not output_dir:
                output_dir = os.path.join(self.cache_dir, video_id)
                
            os.makedirs(output_dir, exist_ok=True)
            
            # 5. 并行处理不同内容类型
            if video_info.get('images'):
                # 图集类型 - 并行下载图片和音频
                logger.info("检测到图集内容，开始并行处理")
                result = self._process_image_gallery_parallel(video_info, output_dir, result)
                
            else:
                # 视频/音频类型 - 并行处理
                logger.info("检测到视频内容，开始并行处理")
                result = self._process_video_parallel(video_info, output_dir, result)
            
            # 6. 检查转录结果、视频帧、视频名、视频id都是全面的, 则success=True, 否则success=False
            if result['transcript'] and result['frames'] and result['video_info']['title'] and result['video_info']['aweme_id']:
                result['success']=True
            else:
                result['success']=False
                
            # 6. 保存到缓存和JSON文件
            if result['success']:
                self.save_cache(video_id, result)
                self._save_result_json(result, output_dir, video_id)
                logger.info("抖音内容处理完成!")
            return result
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"处理抖音内容失败: {e}")
            return result
    
    def _save_result_json(self, result: dict, output_dir: str, video_id: str) -> None:
        """
        保存结果到JSON文件
        
        Args:
            result: 处理结果
            output_dir: 输出目录
            video_id: 视频ID
        """
        try:
            if output_dir:
                json_path = os.path.join(output_dir, f"{video_id}_result.json")
            else:
                json_path = os.path.join(self.cache_dir, video_id, "result.json")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            # 保存结果到JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            logger.info(f"结果已保存到JSON文件: {json_path}")
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")

    def _process_image_gallery_parallel(self, video_info: dict, output_dir: str, result: dict) -> dict:
        """并行处理图集内容"""
        try:
            result['media_type'] = 'images'
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                
                # 并行任务1: 下载图片
                if video_info.get('images'):
                    futures.append(executor.submit(
                        self.download_images, 
                        video_info['images'], 
                        output_dir
                    ))
                
                # 并行任务2: 下载封面
                if video_info.get('cover_url'):
                    cover_path = os.path.join(output_dir, "cover.jpg")
                    futures.append(executor.submit(
                        self.download_file,
                        video_info['cover_url'],
                        cover_path
                    ))
                
                # 并行任务3: 下载音频
                audio_url = video_info.get('audio_url') or video_info.get('video_url')
                if audio_url:
                    futures.append(executor.submit(
                        self.download_audio,
                        audio_url,
                        output_dir
                    ))
                
                # 收集结果
                for i, future in enumerate(as_completed(futures)):
                    try:
                        if i == 0:  # 图片下载
                            result['images'] = future.result()
                        elif i == 1:  # 封面下载
                            if future.result():
                                result['cover_path'] = os.path.join(output_dir, "cover.jpg")
                        elif i == 2:  # 音频下载
                            audio_path = future.result()
                            if audio_path:
                                result['audio_path'] = audio_path
                    except Exception as e:
                        logger.error(f"并行任务失败: {e}")
            
            # 音频转录（需要在音频下载完成后）
            if result.get('audio_path'):
                result['transcript'] = self.transcribe_audio(result['audio_path'])
            
            result['success'] = True
            return result
            
        except Exception as e:
            result['error'] = str(e)
            return result
    
    def _process_video_parallel(self, video_info: dict, output_dir: str, result: dict) -> dict:
        """并行处理视频内容"""
        try:
            media_url = video_info.get('video_url') or video_info.get('audio_url')
            if not media_url:
                result['error'] = "未找到媒体URL"
                return result
            
            # 先下载媒体文件和封面（并行）
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                
                # 任务1: 下载媒体
                futures['media'] = executor.submit(self.download_media, media_url, output_dir)
                
                # 任务2: 下载封面
                if video_info.get('cover_url'):
                    cover_path = os.path.join(output_dir, "cover.jpg")
                    futures['cover'] = executor.submit(
                        self.download_file,
                        video_info['cover_url'], 
                        cover_path
                    )
                
                # 收集下载结果
                media_path, media_type = "", ""
                for task_name, future in futures.items():
                    try:
                        if task_name == 'media':
                            media_path, media_type = future.result()
                            result['media_type'] = media_type
                            if media_path:
                                result['video_path'] = media_path
                        elif task_name == 'cover':
                            if future.result():
                                result['cover_path'] = os.path.join(output_dir, "cover.jpg")
                    except Exception as e:
                        logger.error(f"下载任务 {task_name} 失败: {e}")
            
            # 处理视频文件（需要在下载完成后）
            if media_path and os.path.exists(media_path):
                if media_type == 'video':
                    # 并行处理视频内容
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        futures = {}
                        
                        # 任务1: 提取视频帧
                        futures['frames'] = executor.submit(
                            self.extract_frames_from_video, 
                            media_path, 
                            output_dir
                        )
                        
                        # 任务2: 音频转录
                        futures['transcript'] = executor.submit(
                            self.transcribe_audio, 
                            media_path
                        )
                        
                        # 收集处理结果
                        for task_name, future in futures.items():
                            try:
                                if task_name == 'frames':
                                    result['frames'] = future.result()
                                elif task_name == 'transcript':
                                    result['transcript'] = future.result()
                            except Exception as e:
                                logger.error(f"视频处理任务 {task_name} 失败: {e}")
                
                else:
                    # 纯音频处理
                    result['audio_path'] = media_path
                    result['transcript'] = self.transcribe_audio(media_path)
            
            result['success'] = True
            return result
            
        except Exception as e:
            result['error'] = str(e)
            return result
    
if __name__ == "__main__":
    # 测试示例 - 需要使用tools模块先解析URL
    from tools import parse_url_from_text
    
    crawler = ContentCrawler()
    text = "1.74 复制打开抖音，看看【滴水观音的作品】# 星座 # 摩羯座  https://v.douyin.com/w3Eh2R5sjl8/ U@Y.mQ 09/18 Rkc:/"
    resolved_url = parse_url_from_text(text)
    result = crawler.process_douyin_content(resolved_url)
    print(result)