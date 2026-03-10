import whisper
import ffmpeg
import os
import tempfile
from typing import Dict, Any, Optional
import logging

from .file_detector import FileTypeDetector

logger = logging.getLogger(__name__)

class AudioTranscriptionService:
    
    def __init__(self):
        self.model = None
        self.model_name = 'base'
        self._load_model()
    
    def _load_model(self, model_name: Optional[str] = None):
        try:
            if model_name:
                self.model_name = model_name
            
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading Whisper model: {self.model_name} on {device}")
            self.model = whisper.load_model(self.model_name, device=device)
            self._use_fp16 = device == "cuda"
            logger.info(f"Whisper model {self.model_name} loaded successfully on {device}")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model {self.model_name}: {e}")
            self.model = None
    
    def transcribe_audio_file(
        self, 
        file_path: str, 
        language: Optional[str] = None,
        model_size: str = 'base'
    ) -> Dict[str, Any]:
        try:
            file_info = FileTypeDetector.detect_file_type(file_path)
            if file_info['category'] not in ['audio', 'video']:
                raise ValueError(f"File is not audio or video: {file_path}")
            
            if model_size != self.model_name:
                self._load_model(model_size)
            
            if not self.model:
                raise RuntimeError("Whisper model not available")
            
            audio_path = self._prepare_audio(file_path, file_info['category'])
            
            try:
                logger.info(f"Starting transcription of {file_path}")
                
                transcribe_options = {
                    'fp16': getattr(self, '_use_fp16', False),
                    'verbose': False
                }
                
                if language:
                    transcribe_options['language'] = language
                
                result = self.model.transcribe(audio_path, **transcribe_options)
                
                transcribed_text = result['text'].strip()
                detected_language = result.get('language', 'unknown')
                
                segments = result.get('segments', [])
                total_duration = segments[-1]['end'] if segments else 0
                
                avg_confidence = self._calculate_confidence(segments)
                
                return {
                    'text': transcribed_text,
                    'language': detected_language,
                    'duration': total_duration,
                    'segments_count': len(segments),
                    'confidence': avg_confidence,
                    'model_used': self.model_name,
                    'word_count': len(transcribed_text.split()) if transcribed_text else 0,
                    'status': 'success'
                }
                
            finally:
                if audio_path != file_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                    
        except Exception as e:
            logger.error(f"Audio transcription failed for {file_path}: {e}")
            return {
                'text': '',
                'language': 'unknown',
                'duration': 0,
                'segments_count': 0,
                'confidence': 0,
                'model_used': self.model_name,
                'word_count': 0,
                'status': 'failed',
                'error': str(e)
            }
    
    def _prepare_audio(self, file_path: str, file_category: str) -> str:
        if file_category == 'audio':
            return file_path
        
        try:
            temp_dir = tempfile.gettempdir()
            temp_audio_path = os.path.join(
                temp_dir, 
                f"temp_audio_{os.path.basename(file_path)}.wav"
            )
            
            logger.info(f"Extracting audio from video: {file_path}")
            
            (
                ffmpeg
                .input(file_path)
                .output(temp_audio_path, acodec='pcm_s16le', ar=16000, ac=1)
                .overwrite_output()
                .run(quiet=True, capture_stdout=True)
            )
            
            return temp_audio_path
            
        except Exception as e:
            logger.error(f"Failed to extract audio from {file_path}: {e}")
            raise
    
    def _calculate_confidence(self, segments: list) -> float:
        if not segments:
            return 0.0
        
        total_confidence = 0
        valid_segments = 0
        
        for segment in segments:
            duration = segment.get('end', 0) - segment.get('start', 0)
            words = len(segment.get('text', '').split())
            
            if duration > 0 and words > 0:
                word_rate = words / duration
                confidence = min(1.0, word_rate / 3.0)
                total_confidence += confidence
                valid_segments += 1
        
        return (total_confidence / valid_segments * 100) if valid_segments > 0 else 0.0
    
    def get_supported_formats(self) -> Dict[str, list]:
        return {
            'audio': ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'wma'],
            'video': ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv']
        }
    
    def estimate_processing_time(self, file_path: str) -> Dict[str, Any]:
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['streams'][0]['duration'])
            
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            time_ratios = {
                'tiny': 0.1,
                'base': 0.2,
                'small': 0.3,
                'medium': 0.5,
                'large': 1.0
            }
            
            ratio = time_ratios.get(self.model_name, 0.2)
            estimated_seconds = duration * ratio
            
            return {
                'duration_seconds': duration,
                'file_size_mb': file_size_mb,
                'estimated_processing_seconds': estimated_seconds,
                'model_used': self.model_name
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate processing time for {file_path}: {e}")
            return {
                'duration_seconds': 0,
                'file_size_mb': 0,
                'estimated_processing_seconds': 0,
                'error': str(e)
            }
    
    def transcribe_with_timestamps(
        self, 
        file_path: str, 
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            file_info = FileTypeDetector.detect_file_type(file_path)
            if file_info['category'] not in ['audio', 'video']:
                raise ValueError(f"File is not audio or video: {file_path}")
            
            if not self.model:
                raise RuntimeError("Whisper model not available")
            
            audio_path = self._prepare_audio(file_path, file_info['category'])
            
            try:
                transcribe_options = {
                    'fp16': getattr(self, '_use_fp16', False),
                    'verbose': False,
                    'word_timestamps': True
                }
                
                if language:
                    transcribe_options['language'] = language
                
                result = self.model.transcribe(audio_path, **transcribe_options)
                
                formatted_segments = []
                for segment in result.get('segments', []):
                    formatted_segments.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text'].strip(),
                        'words': segment.get('words', [])
                    })
                
                return {
                    'text': result['text'].strip(),
                    'language': result.get('language', 'unknown'),
                    'segments': formatted_segments,
                    'status': 'success'
                }
                
            finally:
                if audio_path != file_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                    
        except Exception as e:
            logger.error(f"Timestamp transcription failed for {file_path}: {e}")
            return {
                'text': '',
                'language': 'unknown',
                'segments': [],
                'status': 'failed',
                'error': str(e)
            }