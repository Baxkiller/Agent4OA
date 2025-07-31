import os
import requests
import re
import json
from typing import List, Optional, Tuple, Dict, Any
from pydub import AudioSegment
import logging
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from abc import ABC, abstractmethod

# 导入通义听悟语音识别
try:
    from .tongyi_speech_recognizer import create_tongyi_recognizer
    TONGYI_AVAILABLE = True
except ImportError:
    TONGYI_AVAILABLE = False

logger = logging.getLogger(__name__)


class MediaProcessor(ABC):
    """媒体处理基类"""
    
    @abstractmethod
    def process(self, file_path: str, output_dir: str) -> Dict[str, Any]:
        """处理媒体文件"""
        pass


class AudioProcessor(MediaProcessor):
    """音频处理器"""
    
    def __init__(self, speech_recognizer=None):
        self.speech_recognizer = speech_recognizer
    
    def process(self, file_path: str, output_dir: str) -> Dict[str, Any]:
        """处理音频文件"""
        result = {
            'transcript': '',
            'audio_path': file_path,
            'type': 'audio'
        }
        
        try:
            if self.speech_recognizer:
                transcript = self.transcribe_audio(file_path)
                result['transcript'] = transcript or ''
            else:
                logger.warning("未配置语音识别器")
                
            return result
            
        except Exception as e:
            logger.error(f"音频处理失败: {e}")
            return result
    
    def transcribe_audio(self, audio_path: str) -> str:
        """音频转录"""
        try:
            if not os.path.exists(audio_path):
                logger.error(f"音频文件不存在: {audio_path}")
                return ""
            
            logger.info(f"开始语音识别: {os.path.basename(audio_path)}")
            
            if self.speech_recognizer:
                try:
                    logger.info("🔥 使用通义听悟识别...")
                    
                    # 检查文件格式，通义听悟支持多种格式
                    supported_formats = ['.wav', '.mp3', '.m4a', '.mp4', '.aac', '.flac']
                    file_ext = os.path.splitext(audio_path)[1].lower()
                    
                    if file_ext not in supported_formats:
                        logger.warning(f"不支持的音频格式: {file_ext}")
                        return ""
                    
                    result = self.speech_recognizer.recognize_from_file(audio_path, language="zh-CN")
                    
                    if result and result.strip():
                        logger.info(f"✅ 语音识别成功: {len(result)} 字符")
                        return result.strip()
                    else:
                        logger.warning("⚠️ 语音识别返回空结果")
                        
                except Exception as e:
                    import traceback
                    logger.warning(f"⚠️ 语音识别失败: {e}")
                    logger.debug(f"详细错误追踪:\n{traceback.format_exc()}")
            else:
                logger.warning("⚠️ 语音识别器未初始化")
            
            return ""
            
        except Exception as e:
            logger.error(f"语音识别异常: {e}")
            return ""


class VideoProcessor(MediaProcessor):
    """视频处理器"""
    
    def __init__(self, audio_processor: AudioProcessor = None):
        self.audio_processor = audio_processor
    
    def process(self, file_path: str, output_dir: str) -> Dict[str, Any]:
        """处理视频文件"""
        result = {
            'frames': [],
            'transcript': '',
            'audio_path': '',
            'video_path': file_path,
            'type': 'video'
        }
        
        try:
            # 并行处理视频帧和音频转录
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                
                # 任务1: 提取视频帧
                futures['frames'] = executor.submit(
                    self.extract_frames, file_path, output_dir
                )
                
                # 任务2: 提取音频并转录
                if self.audio_processor:
                    futures['audio'] = executor.submit(
                        self.extract_and_transcribe_audio, file_path, output_dir
                    )
                
                # 收集结果
                for task_name, future in futures.items():
                    try:
                        if task_name == 'frames':
                            frames = future.result()
                            result['frames'] = frames or []
                        elif task_name == 'audio':
                            audio_result = future.result()
                            if audio_result:
                                result['transcript'] = audio_result.get('transcript', '') or ''
                                result['audio_path'] = audio_result.get('audio_path', '') or ''
                    except Exception as e:
                        logger.error(f"视频处理任务 {task_name} 失败: {e}")
                        if task_name == 'frames':
                            result['frames'] = []
                        elif task_name == 'audio':
                            result['transcript'] = ''
            
            return result
            
        except Exception as e:
            logger.error(f"视频处理失败: {e}")
            return result
    
    def extract_frames(self, video_path: str, output_dir: str, max_frames: int = 5) -> List[str]:
        """提取视频帧"""
        extracted_frames = []
        
        try:
            logger.info(f"开始从视频提取帧: {os.path.basename(video_path)}")
            
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                logger.error(f"无法打开视频文件: {video_path}")
                return extracted_frames
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"视频信息: {total_frames} 帧, {fps} FPS, {duration:.1f} 秒")
            
            if total_frames <= max_frames:
                frame_indices = list(range(0, total_frames, max(1, total_frames // max_frames)))
            else:
                frame_indices = [i * total_frames // max_frames for i in range(max_frames)]
            
            for i, frame_idx in enumerate(frame_indices):
                if i >= max_frames:
                    break
                    
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    frame_filename = f"frame_{i+1:03d}.jpg"
                    frame_path = os.path.join(output_dir, frame_filename)
                    
                    if cv2.imwrite(frame_path, frame):
                        extracted_frames.append(frame_path)
                        logger.info(f"提取帧 {i+1}: {frame_filename}")
                    else:
                        logger.error(f"保存帧失败: {frame_filename}")
                else:
                    logger.warning(f"读取帧失败: 帧索引 {frame_idx}")
            
            cap.release()
            logger.info(f"视频帧提取完成: {len(extracted_frames)} 帧")
            
            return extracted_frames
            
        except Exception as e:
            logger.error(f"提取视频帧失败: {e}")
            return extracted_frames
    
    def extract_and_transcribe_audio(self, video_path: str, output_dir: str) -> Dict[str, Any]:
        """从视频中提取音频并转录"""
        result = {
            'transcript': '',
            'audio_path': ''
        }
        
        try:
            logger.info(f"🎵 开始从视频提取音频: {os.path.basename(video_path)}")
            
            # 统一修改：提取音频到MP3文件
            audio_filename = "extracted_audio.mp3"
            audio_path = os.path.join(output_dir, audio_filename)
            
            logger.info(f"🔄 提取音频: {os.path.basename(video_path)} -> {audio_filename}")
            
            if self.extract_audio_from_video(video_path, audio_path):
                result['audio_path'] = audio_path
                
                # 统一修改：调试保存的文件也应是mp3
                try:
                    debug_dir = "debug"
                    os.makedirs(debug_dir, exist_ok=True)
                    video_id = os.path.basename(output_dir) # output_dir通常是cache/video_id
                    debug_audio_path = os.path.join(debug_dir, f"{video_id}_problem_audio.mp3")
                    import shutil
                    shutil.copy(audio_path, debug_audio_path)
                    logger.info(f"💾 已保存可疑音频文件以供调试: {debug_audio_path}")
                except Exception as e:
                    logger.warning(f"保存调试音频文件失败: {e}")

                # 使用音频处理器进行转录
                if self.audio_processor:
                    transcript = self.audio_processor.transcribe_audio(audio_path)
                    result['transcript'] = transcript or ''
                else:
                    logger.warning("⚠️ 未配置音频处理器，跳过转录")
            else:
                logger.warning("⚠️ 音频提取失败")
            
            return result
            
        except Exception as e:
            logger.error(f"音频提取和转录失败: {e}")
            return result
    
    def extract_audio_from_video(self, video_path: str, audio_path: str) -> bool:
        """从视频文件中提取音频"""
        try:
            logger.info(f"提取音频: {os.path.basename(video_path)} -> {os.path.basename(audio_path)}")
            
            # 使用pydub提取音频
            audio = AudioSegment.from_file(video_path)
            
            # 统一修改：导出为标准的16kHz, 16-bit, 单声道MP3文件
            standard_audio = audio.set_sample_width(2).set_frame_rate(16000).set_channels(1)
            standard_audio.export(audio_path, format="mp3")
            
            # 新增：验证生成的文件是否有效
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                # WAV文件头约44字节，一个有效的音频文件不应小于1KB
                if file_size < 1024:
                    logger.error(f"❌ 音频提取失败：生成的文件过小 ({file_size} bytes)，可能为空或已损坏。")
                    return False
                
                logger.info(f"✅ 标准化音频提取成功: {os.path.basename(audio_path)} ({file_size} bytes)")
                return True
            else:
                logger.error("❌ 音频提取失败：文件未生成。")
                return False
                
        except Exception as e:
            import traceback
            logger.error(f"音频提取时发生严重错误: {e}")
            logger.debug(traceback.format_exc())
            return False


class ImageProcessor:
    """图片处理器"""
    
    def process(self, image_urls: List[str], output_dir: str, downloader) -> Dict[str, Any]:
        """处理图片列表"""
        result = {
            'images': [],
            'type': 'images'
        }
        
        try:
            if not image_urls:
                logger.info("没有图片需要下载")
                return result
            
            logger.info(f"开始下载 {len(image_urls)} 张图片")
            
            downloaded_images = []
            for i, img_url in enumerate(image_urls):
                try:
                    img_filename = f"image_{i+1:03d}.jpg"
                    img_path = os.path.join(output_dir, img_filename)
                    
                    if downloader.download_file(img_url, img_path):
                        downloaded_images.append(img_path)
                    else:
                        logger.warning(f"图片下载失败: {img_url}")
                        
                except Exception as e:
                    logger.error(f"下载图片 {i+1} 失败: {e}")
            
            result['images'] = downloaded_images
            logger.info(f"图片下载完成: {len(downloaded_images)}/{len(image_urls)}")
            
            return result
            
        except Exception as e:
            logger.error(f"图片处理失败: {e}")
            return result


class FileDownloader:
    """文件下载器"""
    
    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()
    
    def download_file(self, url: str, output_path: str) -> bool:
        """下载文件到指定路径"""
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
    
    def download_media(self, media_url: str, output_dir: str) -> Tuple[str, str]:
        """下载媒体文件并判断类型"""
        try:
            logger.info(f"开始下载媒体: {media_url}")
            
            # 根据URL判断文件类型
            if any(ext in media_url.lower() for ext in ['.mp4', '.mov', '.avi']):
                media_filename = "media.mp4"
                media_type = "video"
            elif any(ext in media_url.lower() for ext in ['.mp3', '.aac']):
                media_filename = "media.mp3"
                media_type = "audio"
            else:
                # 默认为m4a格式（抖音常用）
                media_filename = "media.m4a"
                media_type = "video"  # m4a可能包含视频
            
            media_path = os.path.join(output_dir, media_filename)
            
            if self.download_file(media_url, media_path):
                return media_path, media_type
            else:
                return "", ""
                
        except Exception as e:
            logger.error(f"下载媒体文件失败: {e}")
            return "", ""


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def check_cache(self, video_id: str) -> Optional[dict]:
        """检查本地缓存是否存在"""
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
    
    def save_cache(self, video_id: str, result: dict) -> None:
        """保存结果到缓存"""
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
            # 修正：在缓存查找列表中加入extracted_audio.mp3
            audio_files = ['audio.mp3', 'extracted_audio.mp3', 'media.wav', 'video.wav', 'extracted_audio.wav']
            for filename in audio_files:
                file_path = os.path.join(cache_path, filename)
                if os.path.exists(file_path):
                    updated_result['audio_path'] = file_path
                    break
        
        return updated_result
    

class DouyinInfoExtractor:
    """抖音信息提取器"""
    
    def __init__(self, session: requests.Session):
        self.session = session
    
    def extract_video_info(self, video_url: str) -> Dict[str, Any]:
        """从抖音页面提取视频信息"""
        try:
            logger.info(f"开始提取视频信息: {video_url}")
            
            # 获取页面内容
            response = self.session.get(video_url, timeout=15)
            response.raise_for_status()
            
            # 提取页面中的JSON数据
            html_content = response.text
            
            # 查找_ROUTER_DATA
            router_data_match = re.search(r'_ROUTER_DATA\s*=\s*(\{.*?\});', html_content, re.DOTALL)
            
            if not router_data_match:
                router_data_match = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\});', html_content, re.DOTALL)
            
            if not router_data_match:
                logger.error("未找到_ROUTER_DATA")
                return {}
            
            json_data_str = router_data_match.group(1)
            logger.info(f"提取到JSON数据长度: {len(json_data_str)}")
            
            # 解析JSON数据
            try:
                json_data = json.loads(json_data_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                json_data_str = json_data_str.replace('\\u002F', '/')
                json_data = json.loads(json_data_str)
            
            # 提取视频信息
            try:
                item_list = json_data['loaderData']['video_(id)/page']['videoInfoRes']['item_list'][0]
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"JSON数据结构异常: {e}")
                return {}
            
            # 解析视频信息
            video_info = self._parse_video_info(item_list)
            
            logger.info(f"成功提取视频信息: {video_info['title']}")
            logger.info(f"图片数量: {len(video_info['images'])}")
            logger.info(f"音频URL: {'是' if video_info['audio_url'] else '否'}")
            
            return video_info
            
        except Exception as e:
            logger.error(f"提取视频信息失败: {e}")
            return {}
    
    def _parse_video_info(self, item_list: dict) -> Dict[str, Any]:
        """解析视频信息数据"""
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
        
        return video_info
        

class ContentCrawler:
    """内容爬取服务 - 重构版本，模块化设计"""
    
    def __init__(self, cache_dir: str = "cache"):
        """初始化内容爬虫"""
        # 初始化会话
        self.session = requests.Session()
        # 修正：使用移动端User-Agent和Referer，以获取正确的API数据结构
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
            'referer': 'https://www.douyin.com/?is_from_mobile_home=1&recommend=1'
        })
        
        # 初始化各个组件
        self.cache_manager = CacheManager(cache_dir)
        self.downloader = FileDownloader(self.session)
        self.info_extractor = DouyinInfoExtractor(self.session)
        
        # 初始化语音识别
        speech_recognizer = None
        if TONGYI_AVAILABLE:
            try:
                speech_recognizer = create_tongyi_recognizer()
                logger.info("✅ 通义听悟语音识别已初始化")
            except Exception as e:
                logger.warning(f"⚠️ 通义听悟初始化失败: {e}")
        else:
            logger.warning("⚠️ 通义听悟模块不可用")
        
        # 初始化媒体处理器
        self.audio_processor = AudioProcessor(speech_recognizer)
        self.video_processor = VideoProcessor(self.audio_processor)
        self.image_processor = ImageProcessor()
        
        logger.info("ContentCrawler初始化完成")

    def process_douyin_content(self, resolved_url: str, output_dir: str = None) -> dict:
        """处理抖音内容的完整流程"""
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
            video_info = self.info_extractor.extract_video_info(resolved_url)
            if not video_info:
                result['error'] = "无法提取视频信息"
                return result
                
            result['video_info'] = video_info
            
            # 2. 获取video_id
            video_id = video_info.get('aweme_id')
            if not video_id:
                result['error'] = "无法获取视频ID"
                return result
            
            logger.info(f"✅ 获得video_id: {video_id}")
            
            # 3. 检查缓存
            cached_result = self.cache_manager.check_cache(video_id)
            if cached_result:
                cached_result['from_cache'] = True
                return cached_result
            
            # 4. 设置输出目录
            if not output_dir:
                output_dir = os.path.join(self.cache_manager.cache_dir, video_id)
                
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"📁 输出目录: {output_dir}")
            
            # 5. 分析内容类型并处理
            if video_info.get('images'):
                # 图集内容
                result = self._process_image_content(video_info, output_dir, result)
            else:
                # 视频/音频内容
                result = self._process_media_content(video_info, output_dir, result)
            
            # 6. 保存结果
            if result.get('success'):
                self.cache_manager.save_cache(video_id, result)
                self._save_result_json(result, output_dir, video_id)
                logger.info("✅ 处理成功并已保存")
            else:
                self._save_result_json(result, output_dir, video_id)
                logger.warning("⚠️ 处理未完全成功，已保存调试信息")
                
            return result
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ 处理抖音内容失败: {e}")
            return result
    
    def _process_image_content(self, video_info: dict, output_dir: str, result: dict) -> dict:
        """处理图集内容"""
        try:
            logger.info("🖼️ 检测到图集内容")
            result['media_type'] = 'images'
            
            # 并行下载封面和图片
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                
                # 下载封面
                if video_info.get('cover_url'):
                    cover_path = os.path.join(output_dir, "cover.jpg")
                    futures['cover'] = executor.submit(
                        self.downloader.download_file,
                        video_info['cover_url'],
                        cover_path
                    )
                
                # 下载图片
                if video_info.get('images'):
                    futures['images'] = executor.submit(
                        self.image_processor.process,
                        video_info['images'],
                        output_dir,
                        self.downloader
                    )
                
                # 收集结果
                for task_name, future in futures.items():
                    try:
                        if task_name == 'cover' and future.result():
                                result['cover_path'] = os.path.join(output_dir, "cover.jpg")
                        elif task_name == 'images':
                            image_result = future.result()
                            result['images'] = image_result.get('images', [])
                    except Exception as e:
                        logger.error(f"图集处理任务 {task_name} 失败: {e}")
            
            # 处理音频（如果有）
            audio_url = video_info.get('audio_url') or video_info.get('video_url')
            if audio_url:
                try:
                    media_path, _ = self.downloader.download_media(audio_url, output_dir)
                    if media_path:
                        audio_result = self.audio_processor.process(media_path, output_dir)
                        result['transcript'] = audio_result.get('transcript', '') or ''
                        result['audio_path'] = audio_result.get('audio_path', '') or ''
                except Exception as e:
                    logger.error(f"图集音频处理失败: {e}")
            
            # 判断成功条件
            success_conditions = [
                result.get('cover_path'),
                len(result.get('images', [])) > 0,
                result.get('transcript')
            ]
            
            if any(success_conditions):
                result['success'] = True
                logger.info("✅ 图集内容处理成功")
            else:
                result['error'] = '未获取到有效的图集内容'
                logger.warning("⚠️ 图集内容处理不完整")
            
            return result
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"图集内容处理失败: {e}")
            return result
    
    def _process_media_content(self, video_info: dict, output_dir: str, result: dict) -> dict:
        """处理视频/音频内容"""
        try:
            media_url = video_info.get('video_url') or video_info.get('audio_url')
            if not media_url:
                result['error'] = "未找到媒体URL"
                logger.error("❌ 未找到媒体URL")
                return result
            
            logger.info("🎬 检测到视频/音频内容")
            
            # 并行下载媒体文件和封面
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                
                # 下载媒体
                futures['media'] = executor.submit(
                    self.downloader.download_media, media_url, output_dir
                )
                
                # 下载封面
                if video_info.get('cover_url'):
                    cover_path = os.path.join(output_dir, "cover.jpg")
                    futures['cover'] = executor.submit(
                        self.downloader.download_file,
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
                        elif task_name == 'cover' and future.result():
                                result['cover_path'] = os.path.join(output_dir, "cover.jpg")
                    except Exception as e:
                        logger.error(f"下载任务 {task_name} 失败: {e}")
            
            # 检查是否成功下载了媒体文件
            if not media_path or not os.path.exists(media_path):
                # 检查可能的媒体文件
                potential_files = [
                    os.path.join(output_dir, f) for f in 
                    ["media.m4a", "video.m4a", "video.mp4", "audio.mp3"]
                ]
                
                for potential_file in potential_files:
                    if os.path.exists(potential_file):
                        media_path = potential_file
                        media_type = 'video' if potential_file.endswith(('.m4a', '.mp4')) else 'audio'
                        result['video_path'] = media_path
                        result['media_type'] = media_type
                        logger.info(f"🔍 找到媒体文件: {os.path.basename(media_path)}")
                        break
                
                if not media_path:
                    result['error'] = "未爬取到媒体文件"
                    logger.error("❌ 未爬取到媒体文件")
                    return result
            
            # 处理媒体文件
            if media_path and os.path.exists(media_path):
                logger.info(f"📹 开始处理媒体文件: {os.path.basename(media_path)} (类型: {media_type})")
                
                if media_type == 'video':
                    # 视频处理
                    video_result = self.video_processor.process(media_path, output_dir)
                    result['frames'] = video_result.get('frames', [])
                    result['transcript'] = video_result.get('transcript', '') or ''
                    if video_result.get('audio_path'):
                        result['audio_path'] = video_result['audio_path']
                else:
                    # 纯音频处理
                    audio_result = self.audio_processor.process(media_path, output_dir)
                    result['transcript'] = audio_result.get('transcript', '') or ''
                    result['audio_path'] = audio_result.get('audio_path', '') or ''
            
            # 判断成功条件
            success_conditions = [
                result.get('cover_path'),
                len(result.get('frames', [])) > 0,
                result.get('transcript'),
                result.get('video_path')
            ]
            
            if any(success_conditions):
                result['success'] = True
                logger.info("✅ 媒体内容处理成功")
            else:
                result['error'] = '未获取到有效的媒体内容'
                logger.warning("⚠️ 媒体内容处理不完整")
            
            return result
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"媒体内容处理失败: {e}")
            return result
    
    def _save_result_json(self, result: dict, output_dir: str, video_id: str) -> None:
        """保存结果到JSON文件"""
        try:
            json_path = os.path.join(output_dir, f"{video_id}_result.json")
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            logger.info(f"结果已保存到JSON文件: {json_path}")
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    # 兼容性方法 - 保持原有接口
    def check_cache(self, video_id: str) -> Optional[dict]:
        """检查缓存（兼容性方法）"""
        return self.cache_manager.check_cache(video_id)
    
    def save_cache(self, video_id: str, result: dict) -> None:
        """保存缓存（兼容性方法）"""
        self.cache_manager.save_cache(video_id, result)
    
    def extract_video_info(self, video_url: str) -> Dict[str, Any]:
        """提取视频信息（兼容性方法）"""
        return self.info_extractor.extract_video_info(video_url)
    
    def download_file(self, url: str, output_path: str) -> bool:
        """下载文件（兼容性方法）"""
        return self.downloader.download_file(url, output_path)
    
    def download_images(self, image_urls: List[str], output_dir: str) -> List[str]:
        """下载图片（兼容性方法）"""
        result = self.image_processor.process(image_urls, output_dir, self.downloader)
        return result.get('images', [])
    
    def download_audio(self, audio_url: str, output_dir: str) -> str:
        """下载音频（兼容性方法）"""
        if not audio_url:
            return ""
        
        try:
            if audio_url.endswith('.mp3') or 'mp3' in audio_url:
                audio_filename = "audio.mp3"
            else:
                audio_filename = "audio.m4a"
            
            audio_path = os.path.join(output_dir, audio_filename)
            
            if self.downloader.download_file(audio_url, audio_path):
                return audio_path
            else:
                return ""
                
        except Exception as e:
            logger.error(f"下载音频失败: {e}")
            return ""
    
    def transcribe_audio(self, audio_path: str) -> str:
        """音频转录（兼容性方法）"""
        return self.audio_processor.transcribe_audio(audio_path)
    
    def extract_frames_from_video(self, video_path: str, output_dir: str, max_frames: int = 5) -> List[str]:
        """提取视频帧（兼容性方法）"""
        return self.video_processor.extract_frames(video_path, output_dir, max_frames)
    
    def download_media(self, media_url: str, output_dir: str) -> Tuple[str, str]:
        """下载媒体文件（兼容性方法）"""
        return self.downloader.download_media(media_url, output_dir)

    
if __name__ == "__main__":
    # 测试示例
    # 为了能直接运行此脚本进行测试，需要将项目根目录加入sys.path
    import sys
    import os
    
    # 将项目根目录(Agent4OA)添加到sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        from tools import parse_url_from_text
    except ImportError:
        print("无法导入 parse_url_from_text, 请确保项目结构正确，并从根目录运行。")
        sys.exit(1)
    
    crawler = ContentCrawler()
    source_text = "6.92 复制打开抖音，看看【香辣鱼yuyuyu🐟的作品】我脸那么大看我关瘦脸???🤬😡😤 # 郭子 # 郭... https://v.douyin.com/zMBwcW5TsTQ/ VLw:/ a@n.Qk 01/24 "
    
    print(f"正在解析文本中的URL: {source_text}")
    resolved_url = parse_url_from_text(source_text)
    
    if resolved_url:
        print(f"解析成功，URL: {resolved_url}")
        result = crawler.process_douyin_content(resolved_url)
        print("\n--- 处理结果 ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("--- 处理完成 ---")
    else:
        print("未在文本中找到有效的URL。")