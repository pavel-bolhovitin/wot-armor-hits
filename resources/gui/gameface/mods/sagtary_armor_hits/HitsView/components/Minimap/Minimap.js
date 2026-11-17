// Minimap at the bottom of the hits panel: the selected battle's map seen from above (window.model.minimap), under a
// header, its title at the left, that folds it away and back (the arrow at the right shows which way; for this opening
// of the screen only); hidden without an image of the map. Over the map, the vehicles of the chosen hit's snapshot, a
// mark each, coloured by whose it is (the player's, an ally's, an enemy's).
// The map is a square, the image's, as large as the room under the header lets it be: its side follows the room's
// size. The marks are placed on it in parts of its side, so they stay on their places at any size.
// Its styles are in Minimap.css, linked in HitsView.html.
import { element, withChildren } from "../../common/dom.js";
import { arrayItems } from "../../common/model.js";

// The class of a vehicle's mark by whose it is (the model's kind).
const KIND_CLASSES = {
    player: "minimap__vehiclePlayer",
    ally: "minimap__vehicleAlly",
    enemy: "minimap__vehicleEnemy",
};
// The nodes the drawing fills, made by mountMinimap.
let nodes = null;

// The map's square as large as the room under the header.
function fitSquare() {
    const side = Math.min(nodes.map.clientWidth, nodes.map.clientHeight);
    nodes.square.style.width = `${side}px`;
    nodes.square.style.height = `${side}px`;
}

// Makes the minimap at the end of parent, the hits panel; once, before the first drawing.
export function mountMinimap(parent) {
    const title = element("div", "minimap__title");
    const header = withChildren(element("div", "minimap__header"), [title, element("div", "minimap__arrow")]);
    const square = element("div", "minimap__square");
    const map = withChildren(element("div", "minimap__map"), [square]);
    const root = withChildren(element("div", "minimap"), [header, map]);
    nodes = { root, title, map, square };
    header.addEventListener("click", () => root.classList.toggle("minimap__folded"));
    new ResizeObserver(fitSquare).observe(map);
    parent.appendChild(root);
}

// Draws the map and its vehicles from the model; on every change of it.
export function drawMinimap() {
    const model = window.model && window.model.minimap;
    if (!nodes || !model) {
        return;
    }
    nodes.title.textContent = model.title;
    const image = model.image || "";
    nodes.root.classList.toggle("minimap__visible", Boolean(image));
    nodes.square.style.backgroundImage = image ? `url(${image})` : "none";
    nodes.square.textContent = "";
    arrayItems(model.vehicles).forEach((vehicle) => {
        const mark = element("div", `minimap__vehicle ${KIND_CLASSES[vehicle.kind] || ""}`);
        mark.style.left = `${100 * vehicle.x}%`;
        mark.style.top = `${100 * vehicle.y}%`;
        nodes.square.appendChild(mark);
    });
}
