const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: 6,
  touchDragPaddingPx: 18,
  snapTolerancePx: 16,
};

window.shapeSortConfig = shapeSortConfig;

function usesCoarsePointer() {
  return typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches;
}

function canGrabTile(pointer, tileRect) {
  const padding = usesCoarsePointer()
    ? shapeSortConfig.touchDragPaddingPx
    : shapeSortConfig.dragPaddingPx;

  return (
    pointer.x >= tileRect.left - padding &&
    pointer.x <= tileRect.right + padding &&
    pointer.y >= tileRect.top - padding &&
    pointer.y <= tileRect.bottom + padding
  );
}

window.canGrabShapeSortTile = canGrabTile;
