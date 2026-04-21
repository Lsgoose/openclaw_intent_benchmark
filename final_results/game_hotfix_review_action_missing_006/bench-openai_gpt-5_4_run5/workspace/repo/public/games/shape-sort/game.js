const shapeSortConfig = {
  tileSizePx: 72,
  dragPaddingPx: 6,
  mobileDragPaddingPx: 22,
  mobileBreakpointPx: 768,
  snapTolerancePx: 16,
};

window.shapeSortConfig = shapeSortConfig;

function getGrabPadding() {
  const isSmallScreen = window.matchMedia(`(max-width: ${shapeSortConfig.mobileBreakpointPx}px)`).matches;
  return isSmallScreen ? shapeSortConfig.mobileDragPaddingPx : shapeSortConfig.dragPaddingPx;
}

function canGrabTile(pointer, tileRect) {
  const padding = getGrabPadding();
  return (
    pointer.x >= tileRect.left - padding &&
    pointer.x <= tileRect.right + padding &&
    pointer.y >= tileRect.top - padding &&
    pointer.y <= tileRect.bottom + padding
  );
}

window.canGrabShapeSortTile = canGrabTile;
