const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: 10,
  mobileDragPaddingPx: 22,
  snapTolerancePx: 16,
};

window.shapeSortConfig = shapeSortConfig;

function canGrabTile(pointer, tileRect) {
  const isMobileViewport = window.matchMedia('(max-width: 768px)').matches;
  const padding = isMobileViewport
    ? shapeSortConfig.mobileDragPaddingPx
    : shapeSortConfig.dragPaddingPx;

  return (
    pointer.x >= tileRect.left - padding &&
    pointer.x <= tileRect.right + padding &&
    pointer.y >= tileRect.top - padding &&
    pointer.y <= tileRect.bottom + padding
  );
}

window.canGrabShapeSortTile = canGrabTile;
