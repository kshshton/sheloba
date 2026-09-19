import { getFlatBySlug } from "./flats.js";
import {
  LAYOUTS,
  layoutIndexFor,
  msUntilNextLayout,
  renderFacts,
} from "./dom-layouts.js";

const params = new URLSearchParams(location.search);
const flat = getFlatBySlug(params.get("slug"));

document.title = `${flat.name} · Sheloba`;
document.getElementById("crumb-name").textContent = flat.name;
document.getElementById("gallery").style.backgroundImage = `url("${flat.image}")`;
document.getElementById("address").textContent = `${flat.rooms} · ${flat.address}`;

const facts = document.getElementById("flat-facts");
const note = document.getElementById("layout-note");

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
