import { FLATS } from "./flats.js";

const grid = document.getElementById("listing-grid");

FLATS.forEach((flat) => {
  const card = document.createElement("a");
  card.className = "listing-card";
  card.href = `./flat.html?slug=${encodeURIComponent(flat.slug)}`;

  const photo = document.createElement("div");
  photo.className = "photo";
  photo.style.backgroundImage = `url("${flat.image}")`;

  const body = document.createElement("div");
  body.className = "body";
  body.innerHTML = `<h2>${flat.name}</h2><p>${flat.price} · ${flat.livingSpace}</p>`;

  card.append(photo, body);
  grid.append(card);
});
