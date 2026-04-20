const isCoarsePointer =
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(pointer: coarse)').matches;

const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: isCoarsePointer ? 20 : 10,
  snapTolerancePx: 16,
};

window.shapeSortConfig = shapeSortConfig;

function canGrabTile(pointer, tileRect) {
  const padding = shapeSortConfig.dragPaddingPx;
  return (
    pointer.x >= tileRect.left - padding &&
    pointer.x <= tileRect.right + padding &&
    pointer.y >= tileRect.top - padding &&
    pointer.y <= tileRect.bottom + padding
  );
}

window.canGrabShapeSortTile = canGrabTile;
