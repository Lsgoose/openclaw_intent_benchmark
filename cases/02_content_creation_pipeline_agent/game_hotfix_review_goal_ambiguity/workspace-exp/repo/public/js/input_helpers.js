window.inputHelpers = {
  pointerSlopPx: 8,
  normalizePointer(point) {
    return {
      x: point.clientX,
      y: point.clientY,
    };
  },
};
