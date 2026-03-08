import React, { useMemo } from 'react';
import DocViewer, { DocViewerRenderers } from '@cyntler/react-doc-viewer';
import '@cyntler/react-doc-viewer/dist/index.css';

export default function DocViewerRenderer({ url, filename }) {
  const docs = useMemo(() => [
    { uri: url, fileName: filename }
  ], [url, filename]);

  return (
    <div className="w-full h-full min-h-[500px] rounded-xl overflow-hidden bg-surface-raised shadow-sm">
      <DocViewer 
        documents={docs} 
        pluginRenderers={DocViewerRenderers} 
        config={{
          header: {
            disableHeader: true,
            disableFileName: true,
            retainURLParams: false
          },
          pdfZoom: {
            defaultZoom: 1.1,
            zoomJump: 0.2
          },
        }}
        style={{ width: '100%', height: '100%', backgroundColor: 'transparent' }}
      />
    </div>
  );
}
