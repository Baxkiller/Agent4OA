import os
import cv2
import requests
import tempfile
import subprocess
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import yt_dlp
from moviepy.editor import VideoFileClip
import speech_recognition as sr
from pydub import AudioSegment
import logging

logger = logging.getLogger(__name__)


class ContentCrawler:
    """内容爬取服务"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
    async def extract_video_content(self, video_url: str) -> Tuple[List[str], str]:
        """
        从视频链接提取内容
        返回: (视频帧路径列表, 音频转文字结果)
        """
        try:
            # 下载视频
            video_path = await self._download_video(video_url)
            if not video_path:
                return [], ""
            
            # 提取视频帧
            frames = await self._extract_frames(video_path)
            
            # 提取音频并转文字
            transcript = await self._extract_audio_transcript(video_path)
            
            # 清理临时文件
            if os.path.exists(video_path):
                os.remove(video_path)
                
            return frames, transcript
            
        except Exception as e:
            logger.error(f"视频内容提取失败: {e}")
            return [], ""
    
    async def extract_article_content(self, article_url: str) -> str:
        """从文章链接提取文本内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(article_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 移除脚本和样式元素
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 提取主要文本内容
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.error(f"文章内容提取失败: {e}")
            return ""
    
    async def _download_video(self, video_url: str) -> Optional[str]:
        """下载视频到临时文件"""
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            
            ydl_opts = {
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'format': 'best[height<=720]',  # 限制分辨率以节省空间
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                video_path = ydl.prepare_filename(info)
                
            return video_path if os.path.exists(video_path) else None
            
        except Exception as e:
            logger.error(f"视频下载失败: {e}")
            return None
    
    async def _extract_frames(self, video_path: str, fps: float = 1.0) -> List[str]:
        """从视频中提取帧（默认每秒1帧）"""
        frames = []
        try:
            cap = cv2.VideoCapture(video_path)
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(video_fps / fps)
            
            frame_count = 0
            saved_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % frame_interval == 0:
                    # 保存帧到临时文件
                    temp_dir = tempfile.mkdtemp()
                    frame_path = os.path.join(temp_dir, f"frame_{saved_count:04d}.jpg")
                    cv2.imwrite(frame_path, frame)
                    frames.append(frame_path)
                    saved_count += 1
                
                frame_count += 1
            
            cap.release()
            return frames
            
        except Exception as e:
            logger.error(f"视频帧提取失败: {e}")
            return []
    
    async def _extract_audio_transcript(self, video_path: str) -> str:
        """从视频中提取音频并转换为文字"""
        try:
            # 使用moviepy提取音频
            video = VideoFileClip(video_path)
            audio = video.audio
            
            # 保存音频到临时文件
            temp_dir = tempfile.mkdtemp()
            audio_path = os.path.join(temp_dir, "audio.wav")
            audio.write_audiofile(audio_path, verbose=False, logger=None)
            
            # 使用speech_recognition进行语音识别
            with sr.AudioFile(audio_path) as source:
                audio_data = self.recognizer.record(source)
                try:
                    # 尝试使用Google语音识别
                    transcript = self.recognizer.recognize_google(audio_data, language='zh-CN')
                except sr.UnknownValueError:
                    transcript = ""
                except sr.RequestError:
                    # 如果Google API不可用，尝试使用离线识别
                    try:
                        transcript = self.recognizer.recognize_sphinx(audio_data)
                    except:
                        transcript = ""
            
            # 清理临时文件
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            video.close()
            audio.close()
            
            return transcript
            
        except Exception as e:
            logger.error(f"音频转文字失败: {e}")
            return "" 