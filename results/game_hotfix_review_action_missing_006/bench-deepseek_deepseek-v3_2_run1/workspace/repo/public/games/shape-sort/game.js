const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: 20,  // Increased from 6px for better mobile touch targets
  snapTolerancePx: 16,
};

// Responsive tile size for mobile devices
function getTileSize() {
  if (window.matchMedia && window.matchMedia('(max-width: 768px)').matches) {
    return 88; // Larger tiles on mobile
  }
  return shapeSortConfig.tileSizePx;
}

window.getShapeSortTileSize = getTileSize;

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
