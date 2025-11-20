window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [
      ["\\[", "\\]"],
      ["$$", "$$"],
    ],
    processEscapes: true,
    processEnvironments: true,
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex",
  },
  startup: {
    pageReady: () => {
      return MathJax.startup.defaultPageReady().then(() => {
        console.log("MathJax initial typesetting complete");
      });
    },
  },
};

document$.subscribe(() => {
  MathJax.startup.promise.then(() => {
    MathJax.typesetPromise();
  });
});
