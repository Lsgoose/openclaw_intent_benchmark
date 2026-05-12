window.inputHelpers = {
  pointerSlopPx: 8,
  normalizePointer(point) {
    return {
      x: point.clientX,
      y: point.clientY,
    };
  },
  pointInExpandedRect(point, rect, paddingPx = 0) {
    return (
      point.x >= rect.left - paddingPx &&
      point.x <= rect.right + paddingPx &&
      point.y >= rect.top - paddingPx &&
      point.y <= rect.bottom + paddingPx
    );
  },
};
