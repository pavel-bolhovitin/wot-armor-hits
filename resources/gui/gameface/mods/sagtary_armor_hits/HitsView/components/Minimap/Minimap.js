// Minimap at the bottom of the hits panel: the selected battle's map seen from above (window.model.minimap), under a
// header, its title at the left, that folds it away and back (the arrow at the right shows which way; for this opening
// of the screen only); hidden without an image of the map.
// Its styles are in Minimap.css, linked in HitsView.html.
import { element, withChildren } from "../../common/dom.js";

// The nodes the drawing fills, made by mountMinimap.
let nodes = null;

// Makes the minimap at the end of parent, the hits panel; once, before the first drawing.
export function mountMinimap(parent) {
    const title = element("div", "minimap__title");
    const header = withChildren(element("div", "minimap__header"), [title, element("div", "minimap__arrow")]);
    const map = element("div", "minimap__map");
    const root = withChildren(element("div", "minimap"), [header, map]);
    nodes = { root, title, map };
    header.addEventListener("click", () => root.classList.toggle("minimap__folded"));
    parent.appendChild(root);
}

// Draws the map from the model; on every change of it.
export function drawMinimap() {
    const model = window.model && window.model.minimap;
    if (!nodes || !model) {
        return;
    }
    nodes.title.textContent = model.title;
    const image = model.image || "";
    nodes.root.classList.toggle("minimap__visible", Boolean(image));
    nodes.map.style.backgroundImage = image ? `url(${image})` : "none";
}
