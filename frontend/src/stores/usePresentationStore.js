import { create } from 'zustand';

function mapSlides(slides = []) {
  return (slides || []).map((s, i) => ({
    index: s.index ?? i,
    title: s.title || `Slide ${i + 1}`,
    bullets: s.bullets || [],
    visualStyle: s.visual_style || s.visualStyle || 'modern',
    artifactId: s.artifactId || null,
    imageUrl: s.imageUrl || null,
    status: s.status || 'pending',
  }));
}

const usePresentationStore = create((set, get) => ({
  // ── State ──────────────────────────────────────────
  phase: 'idle', // 'idle' | 'planning' | 'generating' | 'done' | 'error'
  videoPhase: 'idle', // 'idle' | 'scripting' | 'audio' | 'rendering' | 'done' | 'error'
  presentationId: null,
  slides: [],
  themeSpec: null, // { primary, secondary, accent, text, muted, font_family, mood }
  videoId: null,
  videoUrl: null,
  videoDurationMs: 0,
  error: null,
  videoError: null,
  progress: {
    message: '',
    pct: 0,
    slidesCompleted: 0,
    slidesTotal: 0,
  },
  videoProgress: {
    message: '',
  },

  // ── Actions ────────────────────────────────────────

  reset: () =>
    set({
      phase: 'idle',
      videoPhase: 'idle',
      presentationId: null,
      slides: [],
      themeSpec: null,
      videoId: null,
      videoUrl: null,
      videoDurationMs: 0,
      error: null,
      videoError: null,
      progress: { message: '', pct: 0, slidesCompleted: 0, slidesTotal: 0 },
      videoProgress: { message: '' },
    }),

  setPhase: (phase) => set({ phase }),
  setVideoPhase: (videoPhase) => set({ videoPhase }),
  setPresentationId: (presentationId) => set({ presentationId }),
  setThemeSpec: (themeSpec) => set({ themeSpec }),
  setError: (error) => set({ error, phase: error ? 'error' : get().phase }),
  setVideoError: (videoError) => set({ videoError, videoPhase: videoError ? 'error' : get().videoPhase }),

  setPresentationData: (data) => {
    if (!data) return;
    const mappedSlides = mapSlides(data.data?.slides || data.slides || []);
    const slideCount = mappedSlides.length;
    const embeddedVideo = data.video || data.data?.video || null;
    const themeSpec = data.data?.themeSpec || data.themeSpec || null;

    set({
      presentationId: data.id || get().presentationId,
      slides: mappedSlides,
      themeSpec: themeSpec || get().themeSpec,
      phase: slideCount > 0 ? 'done' : get().phase,
      progress: {
        message: slideCount > 0 ? `${slideCount} slides ready` : get().progress.message,
        pct: slideCount > 0 ? 100 : get().progress.pct,
        slidesCompleted: slideCount,
        slidesTotal: slideCount,
      },
      videoId: embeddedVideo?.id || get().videoId,
      videoUrl: embeddedVideo?.videoUrl || get().videoUrl,
      videoDurationMs: embeddedVideo?.duration || embeddedVideo?.durationMs || get().videoDurationMs,
      videoPhase:
        embeddedVideo?.status === 'completed'
          ? 'done'
          : embeddedVideo?.status === 'failed'
            ? 'error'
            : get().videoPhase,
      videoError: embeddedVideo?.error || get().videoError,
    });
  },

  setVideoData: (video) => {
    if (!video) return;
    set({
      videoId: video.id || get().videoId,
      videoUrl: video.videoUrl || get().videoUrl,
      videoDurationMs: video.duration || video.durationMs || get().videoDurationMs,
      videoPhase:
        video.status === 'completed'
          ? 'done'
          : video.status === 'failed'
            ? 'error'
            : get().videoPhase,
      videoError: video.error || (video.status === 'failed' ? 'Video generation failed' : get().videoError),
    });
  },

  // ── WebSocket event handler ────────────────────────
  handleWsEvent: (msg) => {
    const state = get();
    const aliasMap = {
      slide_plan_ready: 'presentation_slide_plan_ready',
      slide_generated: 'presentation_slide_generated',
      script_generated: 'video_script_done',
      audio_generated: 'video_audio_done',
    };
    const type = aliasMap[msg.type] || msg.type;

    switch (type) {
      case 'presentation_status': {
        const phaseMap = {
          planning: 'planning',
          generating: 'generating',
        };
        set({
          phase: phaseMap[msg.phase] || state.phase,
          presentationId: msg.presentationId || state.presentationId,
          progress: {
            ...state.progress,
            message: msg.message || '',
            slidesTotal: msg.slidesTotal || state.progress.slidesTotal,
            slidesCompleted: msg.slidesCompleted ?? state.progress.slidesCompleted,
            pct: msg.slidesTotal
              ? Math.round(((msg.slidesCompleted || 0) / msg.slidesTotal) * 100)
              : 0,
          },
        });
        break;
      }

      case 'presentation_slide_plan_ready': {
        const slides = mapSlides(msg.slides || []);
        set({
          presentationId: msg.presentationId || state.presentationId,
          slides,
          themeSpec: msg.themeSpec || state.themeSpec,
          phase: 'generating',
          progress: {
            message: `Generating ${slides.length} slides...`,
            pct: 0,
            slidesCompleted: 0,
            slidesTotal: slides.length,
          },
        });
        break;
      }

      case 'presentation_slide_generated': {
        const idx = msg.slideIndex;
        const completed = msg.slidesCompleted || 0;
        const total = msg.slidesTotal || state.progress.slidesTotal;

        set({
          presentationId: msg.presentationId || state.presentationId,
          slides: state.slides.map((s) =>
            s.index === idx
              ? {
                  ...s,
                  artifactId: msg.artifactId,
                  imageUrl: msg.imageUrl,
                  status: 'completed',
                }
              : s
          ),
          progress: {
            message: `${completed}/${total} slides generated`,
            pct: total ? Math.round((completed / total) * 100) : 0,
            slidesCompleted: completed,
            slidesTotal: total,
          },
        });
        break;
      }

      case 'presentation_slide_failed': {
        const failIdx = msg.slideIndex;
        const failCompleted = msg.slidesCompleted || 0;
        const failTotal = msg.slidesTotal || state.progress.slidesTotal;

        set({
          slides: state.slides.map((s) =>
            s.index === failIdx ? { ...s, status: 'failed' } : s
          ),
          progress: {
            message: `${failCompleted}/${failTotal} slides processed`,
            pct: failTotal ? Math.round((failCompleted / failTotal) * 100) : 0,
            slidesCompleted: failCompleted,
            slidesTotal: failTotal,
          },
        });
        break;
      }

      case 'presentation_done': {
        const doneSlides = mapSlides(msg.slides || []);
        set({
          phase: 'done',
          presentationId: msg.presentationId || state.presentationId,
          slides: doneSlides.length > 0 ? doneSlides : state.slides,
          themeSpec: msg.themeSpec || state.themeSpec,
          progress: {
            message: `${msg.successCount || 0} slides ready`,
            pct: 100,
            slidesCompleted: msg.slideCount || state.progress.slidesTotal,
            slidesTotal: msg.slideCount || state.progress.slidesTotal,
          },
        });
        break;
      }

      case 'presentation_error': {
        set({
          phase: 'error',
          error: msg.error || 'Presentation generation failed',
        });
        break;
      }

      // ── Video events ──────────────────
      case 'video_scripting': {
        set({
          videoPhase: 'scripting',
          videoId: msg.videoId || state.videoId,
          videoProgress: { message: msg.message || 'Generating narration scripts...' },
        });
        break;
      }

      case 'video_script_done': {
        set({
          videoPhase: 'scripting',
          videoProgress: { message: msg.message || 'Scripts ready' },
        });
        break;
      }

      case 'video_audio':
      case 'video_audio_done': {
        set({
          videoPhase: 'audio',
          videoProgress: { message: msg.message || 'Generating narration audio...' },
        });
        break;
      }

      case 'video_rendering':
      case 'video_merging': {
        set({
          videoPhase: 'rendering',
          videoProgress: { message: msg.message || 'Composing video...' },
        });
        break;
      }

      case 'video_transcribing': {
        set({
          videoPhase: 'rendering',
          videoProgress: { message: msg.message || 'Generating subtitles with Whisper...' },
        });
        break;
      }

      case 'video_rendering_started': {
        set({
          videoPhase: 'rendering',
          videoProgress: { message: msg.message || 'Composing video...' },
        });
        break;
      }

      case 'video_done': {
        set({
          videoPhase: 'done',
          videoId: msg.videoId || state.videoId,
          videoUrl: msg.videoUrl || null,
          videoDurationMs: msg.durationMs || 0,
          videoProgress: { message: 'Video complete!' },
        });
        break;
      }

      case 'video_error': {
        set({
          videoPhase: 'error',
          videoError: msg.error || 'Video generation failed',
          videoProgress: { message: '' },
        });
        break;
      }

      default:
        break;
    }
  },
}));

export default usePresentationStore;
