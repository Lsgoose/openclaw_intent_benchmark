const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: 6,
  snapTolerancePx: 16,
  // Mobile-friendly: larger touch targets on small screens
  get effectiveDragPaddingPx() {
    const isTouch = window.matchMedia('(pointer: coarse)').matches;
    return isTouch ? 24 : this.dragPaddingPx;
  },
};

window.shapeSortConfig = shapeSortConfig;

function canGrabTile(pointer, tileRect) {
  const padding = shapeSortConfig.effectiveDragPaddingPx;
  return (
    pointer.x >= tileRect.left - padding &&
    pointer.x <= tileRect.right + padding &&
    pointer.y >= tileRect.top - padding &&
    pointer.y <= tileRect.bottom + padding
  );
}

window.canGrabShapeSortTile = canGrabTile;
