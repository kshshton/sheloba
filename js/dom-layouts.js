const INTERVAL_MS = 60_000;

function el(tag, className, text, extra = {}) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  Object.entries(extra).forEach(([key, value]) => {
    if (key === "dataset") {
      Object.assign(node.dataset, value);
    } else if (value != null) {
      node.setAttribute(key, value);
    }
  });
  return node;
}

function labeled(tag, className, label, value, extra) {
  const wrap = el(tag, className, null, extra);
  wrap.append(el("span", "label", label), document.createTextNode(" " + value));
  return wrap;
}

export const LAYOUTS = [
  {
    name: "paragraphs-and-heading",
    build(flat) {
      const root = el("div", "facts-stack");
      root.append(
        el("p", "price", flat.price),
        el("h1", "name", flat.name),
        el("span", "living-space", flat.livingSpace),
        el("div", "id", flat.id)
      );
      return root;
    },
  },
  {
    name: "anchor-card",
    build(flat) {
      const root = el("article", "offer-card");
      root.append(
        el("a", "asking-price", flat.price, { href: "#enquire" }),
        el("h2", "property-title", flat.name),
        el("p", "area-m2", flat.livingSpace),
        el("code", "listing-ref", flat.id)
      );
      return root;
    },
  },
  {
    name: "definition-list",
    build(flat) {
      const root = el("dl", "kv spec-list");
      const rows = [
        ["Price", "offer-amount", flat.price],
        ["Name", "unit-heading", flat.name],
        ["Living space", "floor-area", flat.livingSpace],
        ["ID", "object-key", flat.id],
      ];
      rows.forEach(([label, className, value]) => {
        root.append(el("dt", null, label), el("dd", className, value));
      });
      return root;
    },
  },
  {
    name: "table-rows",
    build(flat) {
      const table = el("table", "specs inventory");
      const body = el("tbody");
      [
        ["sale-figure", "Price", flat.price],
        ["listing-name", "Name", flat.name],
        ["space-chip", "Living space", flat.livingSpace],
        ["sku", "ID", flat.id],
      ].forEach(([className, label, value]) => {
        const tr = el("tr");
        tr.append(el("th", null, label), el("td", className, value));
        body.append(tr);
      });
      table.append(body);
      return table;
    },
  },
  {
    name: "nested-list-buttons",
    build(flat) {
      const list = el("ul", "bullets fact-rail");
      list.append(
        el("li", null, null, { dataset: { field: "price" } }),
        el("li", null, null, { dataset: { field: "name" } }),
        el("li", null, null, { dataset: { field: "livingSpace" } }),
        el("li", null, null, { dataset: { field: "id" } })
      );
      list.children[0].append(el("button", "cost-badge", flat.price, { type: "button" }));
      list.children[1].append(el("a", "home-label", flat.name, { href: "#gallery" }));
      list.children[2].append(el("small", "sqm-value", flat.livingSpace));
      list.children[3].append(el("time", "ref-code", flat.id));
      return list;
    },
  },
];

export function layoutIndexFor(now = Date.now()) {
  return Math.floor(now / INTERVAL_MS) % LAYOUTS.length;
}

export function msUntilNextLayout(now = Date.now()) {
  return INTERVAL_MS - (now % INTERVAL_MS);
}

export function renderFacts(container, flat, now = Date.now()) {
  const layout = LAYOUTS[layoutIndexFor(now)];
  container.replaceChildren(layout.build(flat));
  container.dataset.layout = layout.name;
  return layout;
}
