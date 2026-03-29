'use client';

import { useState, useRef, useCallback } from 'react';
import { useToast } from '@/stores/useToastStore';
import { transcribeAudio } from '@/lib/api/chat';


export default function useMicInput({ onTranscript } = {}) {
  const toast = useToast();
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250);
      setIsRecording(true);
    } catch (err) {
      toast.error('Microphone access denied');
      console.error('Mic error:', err);
    }
  }, [toast]);

  const stop = useCallback(() => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        recorder.onstop = async () => {
          recorder.stream?.getTracks().forEach((t) => t.stop());
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
          if (blob.size > 0 && onTranscript) {
            setIsTranscribing(true);
            try {
              const res = await transcribeAudio(blob, '', 'base');
              const text = String(res?.text || '').trim();
              if (text) {
                onTranscript(text);
              } else {
                toast.info('No clear speech detected. Please try again.');
              }
            } catch (err) {
              toast.error(err?.message || 'Voice transcription failed');
            } finally {
              setIsTranscribing(false);
            }
          }
          resolve(blob);
        };
        recorder.stop();
      } else {
        resolve(null);
      }
      setIsRecording(false);
    });
  }, [onTranscript, toast]);

  const cancel = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
      recorder.stream?.getTracks().forEach((t) => t.stop());
    }
    setIsRecording(false);
    chunksRef.current = [];
  }, []);

  return { isRecording, isTranscribing, start, stop, cancel };
}
