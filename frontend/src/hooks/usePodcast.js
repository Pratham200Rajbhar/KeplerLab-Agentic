'use client';

import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';


export default function usePodcast() {
  const podcast = usePodcastStore();
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const draftMode = useAppStore((s) => s.draftMode);

  const create = async (config) => {
    if (!currentNotebook?.id) throw new Error('No notebook selected');
    return podcast.create(config, currentNotebook.id, selectedSources);
  };

  const loadSessions = () => {
    if (currentNotebook?.id) {
      podcast.loadSessions(currentNotebook.id, draftMode);
    }
  };

  return {
    ...podcast,
    currentNotebook,
    selectedSources,
    draftMode,
    create,
    loadSessions,
  };
}
