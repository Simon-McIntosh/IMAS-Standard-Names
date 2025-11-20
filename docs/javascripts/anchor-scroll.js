// Handle anchor scrolling with mkdocs-material instant navigation
document$.subscribe(function () {
  // Check if there's a hash in the URL
  if (window.location.hash) {
    // Small delay to ensure DOM is ready
    setTimeout(function () {
      const hash = window.location.hash;
      const element = document.querySelector(hash);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 100);
  }
});
