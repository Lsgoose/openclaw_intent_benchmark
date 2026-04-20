const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: 6,
  touchDragPaddingPx: 22,
  snapTolerancePx: 16,
};

window.shapeSortConfig = shapeSortConfig;

function canGrabTile(pointer, tileRect) {
  const isTouchPointer =
    pointer != null &&
    (pointer.pointerType === 'touch' || pointer.type === 'touchstart' || pointer.type === 'touchmove');
  const padding = isTouchPointer
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
