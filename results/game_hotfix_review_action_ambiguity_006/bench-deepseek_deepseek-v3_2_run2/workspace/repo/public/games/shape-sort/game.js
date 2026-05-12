const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: 20, // Increased from 6px for better mobile touch targets
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
