"use strict";
(() => {
  const search = document.getElementById("procedure-search");
  const product = document.getElementById("product-filter");
  const task = document.getElementById("task-filter");
  const cards = [...document.querySelectorAll(".procedure-card")];
  const counter = document.getElementById("result-count");
  const empty = document.getElementById("no-results");
  const normalize = value => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  function filter() {
    const words = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    for (const card of cards) {
      const content = normalize(`${card.dataset.search} ${card.textContent}`);
      const matches = (product.value === "all" || product.value === card.dataset.product)
        && (task.value === "all" || card.dataset.tasks.split(" ").includes(task.value))
        && words.every(word => content.includes(word));
      card.hidden = !matches;
      if (matches) count++;
    }
    counter.textContent = `${count} ${count === 1 ? "procedimento" : "procedimentos"}${count !== cards.length ? ` de ${cards.length}` : ""}`;
    empty.hidden = count !== 0;
  }
  function clear() {search.value = "";product.value = "all";task.value = "all";filter();search.focus();}
  search.addEventListener("input", filter);
  product.addEventListener("change", filter);
  task.addEventListener("change", filter);
  document.getElementById("clear-filters").addEventListener("click", clear);
  document.getElementById("empty-clear-filters").addEventListener("click", clear);
  filter();
})();
