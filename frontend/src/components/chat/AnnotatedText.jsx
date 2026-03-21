'use client';

import React, { useMemo, useState } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import CollapsibleActionBlock from './CollapsibleActionBlock';

/**
 * AnnotatedText renders content and injects interactive underlines for associated action blocks.
 * 
 * @param {string} content - The actual text of the block
 * @param {Array} annotations - List of response blocks associated with this block
 * Each annotation should have: { text: "[action:parent_id:selection] actual_response", id: "block_id" }
 */
export default function AnnotatedText({ content, annotations = [] }) {
  const [openIds, setOpenIds] = useState({});

  // Parse annotations to extract selection and type
  const parsedAnnotations = useMemo(() => {
    return annotations.map(ann => {
      // Format: [action:parent_id:selection] body
      const match = ann.text.match(/^\[(translate|ask|simplify|explain):([^:]+):?([^\]]*)\]\s*(.*)/s);
      if (!match) return null;
      return {
        id: ann.id,
        action: match[1],
        parentId: match[2],
        selection: match[3],
        body: match[4],
        fullText: ann.text
      };
    }).filter(Boolean);
  }, [annotations]);

  // To implement inline underlining, we'll replace the selection string with a span.
  const annotatedContent = useMemo(() => {
    let result = content;
    parsedAnnotations.forEach(ann => {
      if (!ann.selection || ann.selection.length < 3) return;
      
      const escapedSelection = ann.selection.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(escapedSelection, 'g');
      
      // Add data-ann-id to link the click
      result = result.replace(regex, `<span class="selection-underline" data-action="${ann.action}" data-ann-id="${ann.id}">${ann.selection}</span>`);
    });
    return result;
  }, [content, parsedAnnotations]);

  const handleContainerClick = (e) => {
    const underline = e.target.closest('.selection-underline');
    if (underline) {
      const annId = underline.getAttribute('data-ann-id');
      if (annId) {
        setOpenIds(prev => ({ ...prev, [annId]: !prev[annId] }));
      }
    }
  };

  return (
    <div className="group/annotated relative" onClick={handleContainerClick}>
      <div className="prose-chat prose-invert max-w-none">
        <MarkdownRenderer content={annotatedContent} />
      </div>
      
      {parsedAnnotations.length > 0 && (
        <div className="mt-4 space-y-2">
          {parsedAnnotations.map((ann) => (
            <CollapsibleActionBlock 
              key={ann.id} 
              content={ann.fullText}
              isOpen={!!openIds[ann.id]}
              onToggle={() => setOpenIds(prev => ({ ...prev, [ann.id]: !prev[ann.id] }))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
