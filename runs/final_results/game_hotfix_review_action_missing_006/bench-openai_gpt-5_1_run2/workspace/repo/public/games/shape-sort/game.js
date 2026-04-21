const shapeSortConfig = {
  tileSizePx: 72,
  // Make grab targets more forgiving on touch devices.
  // Increasing this too far can cause accidental grabs when scrolling,
  // so keep it in a reasonable range.
  dragPaddingPx: 18,
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
