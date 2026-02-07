'use client';

import { useCallback, useRef, useState } from 'react';

const MIN_WIDTH = 200;
const MAX_WIDTH = 600;
const DEFAULT_WIDTH = 256;

export default function Sidebar({ children }: { children?: React.ReactNode }) {
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const dragging = useRef(false);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      const startX = e.clientX;
      const startWidth = width;

      const onMouseMove = (moveEvent: MouseEvent) => {
        if (!dragging.current) return;
        const newWidth = startWidth + (moveEvent.clientX - startX);
        setWidth(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, newWidth)));
      };

      const onMouseUp = () => {
        dragging.current = false;
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };

      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },
    [width]
  );

  return (
    <aside
      className="relative hidden shrink-0 overflow-y-auto border-r border-gray-200 bg-gray-50 p-4 md:block"
      style={{ width }}
    >
      {children ?? (
        <p className="text-sm text-gray-500">Select a title to browse</p>
      )}
      {/* Drag handle */}
      <div
        onMouseDown={onMouseDown}
        className="hover:bg-primary-200 active:bg-primary-300 absolute inset-y-0 -right-1 w-2 cursor-col-resize"
        role="separator"
        aria-orientation="vertical"
      />
    </aside>
  );
}
