const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: 6,
  touchDragPaddingPx: 20,
  snapTolerancePx: 16,
};

window.shapeSortConfig = shapeSortConfig;

function canGrabTile(pointer, tileRect) {
  const isTouch = Boolean(
    pointer &&
      (pointer.pointerType === 'touch' ||
        pointer.pointerType === 'pen' ||
        ('ontouchstart' in window && pointer.pointerType !== 'mouse'))
  );
  const padding = isTouch
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
