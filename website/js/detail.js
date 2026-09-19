import {
  LAYOUTS,
  layoutIndexFor,
  msUntilNextLayout,
  renderFacts,
} from "./dom-layouts.js";

const facts = document.getElementById("flat-facts");
const note = document.getElementById("layout-note");
const flat = {
  price: facts.dataset.price,
  name: facts.dataset.name,
  livingSpace: facts.dataset.livingSpace,
  id: facts.dataset.id,
};

function paintFacts() {
  renderFacts(facts, flat);
}

function paintFooter() {
  const remaining = Math.ceil(msUntilNextLayout() / 1000);
  const layout = LAYOUTS[layoutIndexFor()];
  note.textContent = `DOM layout: ${layout.name} · next structure in ${remaining}s`;
}

function scheduleFacts() {
  setTimeout(() => {
    paintFacts();
    scheduleFacts();
  }, msUntilNextLayout() + 25);
}

paintFacts();
paintFooter();
scheduleFacts();
setInterval(paintFooter, 1000);
