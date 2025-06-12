import re
import requests
import logging
from typing import List

logger = logging.getLogger(__name__)


class URLTools:
    """URL相关工具类"""
    
    def __init__(self):
        self.session = requests.Session()
        # 设置请求头
        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
            'referer': 'https://www.douyin.com/?is_from_mobile_home=1&recommend=1'
        })
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """
        从不规则文本中提取URL
        
        Args:
            text: 包含URL的文本
            
        Returns:
            提取到的URL列表
        """
        try:
            # 匹配以http或https开头，遇到空格为止的URL
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, text)
            
            logger.info(f"从文本中提取到 {len(urls)} 个URL")
            
            # 去重并返回
            unique_urls = list(set(urls))
            
            if unique_urls:
                logger.info(f"去重后保留 {len(unique_urls)} 个URL: {unique_urls}")
            else:
                logger.info("未在文本中找到任何URL")
                
            return unique_urls
            
        except Exception as e:
            logger.error(f"URL提取失败: {e}")
            return []
    
    def resolve_douyin_url(self, url: str) -> str:
        """
        解析抖音链接，支持多种格式并转换为分享链接格式
        
        Args:
            url: 抖音链接
            
        Returns:
            解析后的URL
        """
        try:
            logger.info(f"开始解析URL: {url}")
            
            # 1. 处理短链接 (v.douyin.com等) - 通过重定向获取真实链接
            if any(domain in url for domain in ['v.douyin.com', 'dy.app']):
                logger.info("检测到抖音短链接，发起重定向请求")
                
                try:
                    response = self.session.head(url, allow_redirects=True, timeout=10)
                    
                    if response.url != url:
                        redirected_url = response.url
                        logger.info(f"重定向获取到: {redirected_url}")
                        return self.resolve_douyin_url(redirected_url)
                    else:
                        response = self.session.get(url, allow_redirects=True, timeout=10)
                        final_url = response.url
                        logger.info(f"GET请求后的最终链接: {final_url}")
                        return self.resolve_douyin_url(final_url)
                        
                except Exception as e:
                    logger.error(f"重定向请求失败: {e}")
                    return url
            
            # 2. 标准链接转换为分享链接格式 (API需要这种格式)
            if 'douyin.com/video' in url:
                video_id_match = re.search(r'/video/(\d+)', url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    # 转换为分享链接格式，API更容易处理
                    share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"
                    logger.info(f"标准链接转换为分享格式: {share_url}")
                    return share_url
            
            # 3. 分享链接直接返回
            if 'iesdouyin.com' in url:
                logger.info("已是分享链接格式")
                return url
            
            # 4. 其他格式，原样返回
            logger.warning(f"未识别的URL格式: {url}")
            return url
            
        except Exception as e:
            logger.error(f"URL解析失败: {e}")
            return url
    
    def parse_url_from_text(self, text: str) -> str:
        """
        从文本中提取并解析第一个抖音URL
        
        Args:
            text: 包含URL的文本
            
        Returns:
            解析后的URL，如果没有找到返回None
        """
        url_list_in_text = self.extract_urls_from_text(text)
        if url_list_in_text:
            url_in_text = url_list_in_text[0]
            return self.resolve_douyin_url(url_in_text)
        else:
            return None


# 创建全局实例
url_tools = URLTools()

# 便捷函数
def extract_urls_from_text(text: str) -> List[str]:
    """从文本中提取URL"""
    return url_tools.extract_urls_from_text(text)

def resolve_douyin_url(url: str) -> str:
    """解析抖音URL"""
    return url_tools.resolve_douyin_url(url)

def parse_url_from_text(text: str) -> str:
    """从文本中提取并解析第一个抖音URL"""
    return url_tools.parse_url_from_text(text)
