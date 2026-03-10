import re
from urllib.parse import urlparse
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import yt_dlp
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class YouTubeService:
    
    def __init__(self):
        self.formatter = TextFormatter()
        self.ytt_api = YouTubeTranscriptApi()
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    def extract_transcript_from_url(self, url: str, language: str = 'en') -> Dict[str, Any]:
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                raise ValueError(f"Could not extract video ID from URL: {url}")
            
            metadata = self._get_video_metadata(url)
            
            transcript_result = self._get_transcript(video_id, language)
            
            result = {
                'url': url,
                'video_id': video_id,
                'title': metadata.get('title', ''),
                'description': metadata.get('description', ''),
                'duration': metadata.get('duration', 0),
                'uploader': metadata.get('uploader', ''),
                'upload_date': metadata.get('upload_date', ''),
                'view_count': metadata.get('view_count', 0),
                'transcript': transcript_result['text'],
                'transcript_language': transcript_result['language'],
                'transcript_source': transcript_result['source'],
                'word_count': len(transcript_result['text'].split()) if transcript_result['text'] else 0,
                'status': 'success' if transcript_result['text'] else 'no_transcript'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"YouTube transcript extraction failed for {url}: {e}")
            return {
                'url': url,
                'video_id': '',
                'title': '',
                'description': '',
                'transcript': '',
                'status': 'failed',
                'error': str(e),
                'word_count': 0
            }
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/v/([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _get_transcript(self, video_id: str, preferred_language: str = 'en') -> Dict[str, Any]:
        try:
            fetched = self.ytt_api.fetch(video_id, languages=[preferred_language])
            text = self.formatter.format_transcript(fetched)
            clean_text = self._clean_transcript_text(text)
            
            return {
                'text': clean_text,
                'language': fetched.language_code,
                'source': 'auto' if fetched.is_generated else 'manual',
                'entries_count': len(fetched)
            }
        except Exception as e:
            logger.warning(f"Failed to fetch transcript with preferred language '{preferred_language}' for {video_id}: {e}")
        
        try:
            transcript_list = self.ytt_api.list(video_id)
            
            transcript = None
            try:
                transcript = transcript_list.find_manually_created_transcript([preferred_language, 'en'])
            except Exception:
                pass
            
            if not transcript:
                try:
                    transcript = transcript_list.find_generated_transcript([preferred_language, 'en'])
                except Exception:
                    pass
            
            if not transcript:
                try:
                    available = list(transcript_list)
                    if available:
                        transcript = available[0]
                except Exception:
                    pass
            
            if transcript:
                fetched = transcript.fetch()
                text = self.formatter.format_transcript(fetched)
                clean_text = self._clean_transcript_text(text)
                
                return {
                    'text': clean_text,
                    'language': transcript.language_code,
                    'source': 'auto' if transcript.is_generated else 'manual',
                    'entries_count': len(fetched)
                }
        except Exception as e:
            logger.error(f"Failed to get any transcript for video {video_id}: {e}")
        
        return {
            'text': '',
            'language': '',
            'source': 'none',
            'entries_count': 0
        }
    
    def _get_video_metadata(self, url: str) -> Dict[str, Any]:
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', [])
                }
                
        except Exception as e:
            logger.warning(f"Failed to get video metadata for {url}: {e}")
            return {}
    
    def _clean_transcript_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
            
            metadata = self._get_video_metadata(url)
            
            return {
                'url': url,
                'video_id': video_id,
                'title': metadata.get('title', ''),
                'description': metadata.get('description', ''),
                'duration': metadata.get('duration', 0),
                'uploader': metadata.get('uploader', ''),
                'thumbnail': metadata.get('thumbnail', ''),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to get YouTube video info for {url}: {e}")
            return {
                'url': url,
                'status': 'failed',
                'error': str(e)
            }
    
    def is_youtube_url(self, url: str) -> bool:
        youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com', 'www.youtube.com']
        parsed = urlparse(url)
        return any(domain in parsed.netloc.lower() for domain in youtube_domains)
    
    def get_available_transcripts(self, url: str) -> List[Dict[str, Any]]:
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                return []
            
            transcript_list = self.ytt_api.list(video_id)
            
            transcripts = []
            for transcript in transcript_list:
                transcripts.append({
                    'language_code': transcript.language_code,
                    'language_name': transcript.language,
                    'is_generated': transcript.is_generated,
                    'is_translatable': transcript.is_translatable
                })
            
            return transcripts
            
        except Exception as e:
            logger.error(f"Failed to get available transcripts for {url}: {e}")
            return []