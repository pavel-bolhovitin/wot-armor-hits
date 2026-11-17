// Minimap at the bottom of the hits panel: the selected battle's map seen from above (window.model.minimap), under a
// header, its title at the left, that folds it away and back (the arrow at the right shows which way; for this opening
// of the screen only); hidden without an image of the map. Over the map, the vehicles of the chosen hit's snapshot, as
// on the battle's minimap: the icons of the client's battle atlas, cut out of its texture (the model gives each one's
// place in it), the player's arrow turned to its hull's heading; a plain square of the vehicle's kind (the player's,
// an ally's, an enemy's) when it has no icon. Under all the icons, drawn before them, the corner of each turret the
// client saw: the mod's own image, turned to the turret's heading.
// The map is a square, the image's, as large as the room under the header lets it be: its side follows the room's
// size. The marks are placed on it in parts of its side, so they stay on their places at any size; their size follows
// the side as on the battle's minimap (iconScale).
// Its styles are in Minimap.css, linked in HitsView.html.
import { element, withChildren } from "../../common/dom.js";
import { arrayItems } from "../../common/model.js";

// The class of a plain mark by whose vehicle it is (the model's kind).
const KIND_CLASSES = {
    player: "minimap__vehiclePlayer",
    ally: "minimap__vehicleAlly",
    enemy: "minimap__vehicleEnemy",
};
// The battle's minimap (MinimapSizeConst): its sizes in pixels and the scale of the vehicles' icons at each
// (ENTRY_SCALES), within its entries, which scale with the map from its own size, MAP_BASE pixels (not in the client's
// code: worked out from a screenshot of the largest minimap). The player's arrow scales with the map only.
const BATTLE_SIZES = [210, 260, 310, 390, 490, 610];
const ENTRY_SCALES = [1, 0.9038461538461539, 0.8387096774193548, 0.7692307692307692, 0.7142857142857142,
    0.6721311475409837];
const MAP_BASE = 1000;
// The mod's own factor of all the icons' size over the battle's, for the screen's smaller map.
const ICON_FACTOR = 1.5;
// The turret's corner (Minimap.css: its image by the vehicle's kind): its size in its image's pixels, its apex in the
// middle of its bottom; drawn at twice its size, so it is scaled as a vehicle's icon is (iconScale).
const TURRET_CLASSES = {
    player: "minimap__turretPlayer",
    ally: "minimap__turretAlly",
    enemy: "minimap__turretEnemy",
};
const TURRET_WIDTH = 60;
const TURRET_HEIGHT = 70;
// The nodes the drawing fills, made by mountMinimap, and the map's side in pixels.
let nodes = null;
let side = 0;

// The scale of an icon (atlas pixels to screen pixels) on the map of the side, as the battle's minimap of that size
// has it, between its sizes in a straight line, not below its smallest; times ICON_FACTOR.
function iconScale(kind) {
    return ICON_FACTOR * battleIconScale(kind);
}

function battleIconScale(kind) {
    const size = Math.max(side, BATTLE_SIZES[0]);
    if (kind === "player") {
        return size / MAP_BASE;
    }
    let entryScale = ENTRY_SCALES[ENTRY_SCALES.length - 1];
    for (let index = 1; index < BATTLE_SIZES.length; index++) {
        if (size <= BATTLE_SIZES[index]) {
            const part = (size - BATTLE_SIZES[index - 1]) / (BATTLE_SIZES[index] - BATTLE_SIZES[index - 1]);
            entryScale = ENTRY_SCALES[index - 1] + part * (ENTRY_SCALES[index] - ENTRY_SCALES[index - 1]);
            break;
        }
    }
    return (size / MAP_BASE) * entryScale;
}

// The map's square as large as the room under the header; the marks drawn again for their size.
function fitSquare() {
    side = Math.min(nodes.map.clientWidth, nodes.map.clientHeight);
    nodes.square.style.width = `${side}px`;
    nodes.square.style.height = `${side}px`;
    drawMinimap();
}

// A vehicle's turret corner: its apex on the vehicle's place, turned to the turret's heading and scaled about it.
function turretMark(vehicle) {
    const mark = element("div", `minimap__turret ${TURRET_CLASSES[vehicle.kind] || ""}`);
    const style = mark.style;
    style.left = `${100 * vehicle.x}%`;
    style.top = `${100 * vehicle.y}%`;
    style.width = `${TURRET_WIDTH}px`;
    style.height = `${TURRET_HEIGHT}px`;
    style.marginLeft = `${-TURRET_WIDTH / 2}px`;
    style.marginTop = `${-TURRET_HEIGHT}px`;
    const degrees = (vehicle.turret * 180) / Math.PI;
    style.transform = `rotate(${degrees}deg) scale(${iconScale("ally")})`;
    return mark;
}

// A vehicle's mark: its icon cut out of the atlas, its anchor on the vehicle's place, scaled and turned about it.
function vehicleMark(vehicle, atlas) {
    if (!atlas || !(vehicle.iconWidth > 0)) {
        const mark = element("div", `minimap__vehicle ${KIND_CLASSES[vehicle.kind] || ""}`);
        mark.style.left = `${100 * vehicle.x}%`;
        mark.style.top = `${100 * vehicle.y}%`;
        return mark;
    }
    const mark = element("div", "minimap__vehicleIcon");
    const style = mark.style;
    style.left = `${100 * vehicle.x}%`;
    style.top = `${100 * vehicle.y}%`;
    style.width = `${vehicle.iconWidth}px`;
    style.height = `${vehicle.iconHeight}px`;
    style.marginLeft = `${-vehicle.anchorX}px`;
    style.marginTop = `${-vehicle.anchorY}px`;
    style.backgroundImage = `url(${atlas})`;
    style.backgroundPosition = `${-vehicle.iconX}px ${-vehicle.iconY}px`;
    style.transformOrigin = `${vehicle.anchorX}px ${vehicle.anchorY}px`;
    const degrees = (vehicle.rotation * 180) / Math.PI;
    style.transform = `scale(${iconScale(vehicle.kind)}) rotate(${degrees}deg)`;
    return mark;
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

// Draws the map and its vehicles from the model; on every change of it and of the map's size.
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
    // First all the turrets' corners, then all the icons over them, both in the model's order.
    const vehicles = arrayItems(model.vehicles);
    vehicles.forEach((vehicle) => {
        if (vehicle.hasTurret) {
            nodes.square.appendChild(turretMark(vehicle));
        }
    });
    vehicles.forEach((vehicle) => nodes.square.appendChild(vehicleMark(vehicle, model.atlas)));
}
