// Mobile hotfix:
// - Increase tile size + drag padding so touch targets are easier to hit
// - Slightly loosen snap tolerance so drops feel less finicky
const shapeSortConfig = {
  tileSizePx: 88,
  dragPaddingPx: 14,
  snapTolerancePx: 22,
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
