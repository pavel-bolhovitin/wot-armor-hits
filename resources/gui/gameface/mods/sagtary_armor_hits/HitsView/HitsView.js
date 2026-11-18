import { element } from "./common/dom.js";
import { arrayItems } from "./common/model.js";
import { clientTooltip } from "./common/tooltip.js";
import { drawBugButton, mountBugButton } from "./components/BugButton/BugButton.js";
import { drawHitsPanel, mountHitsPanel } from "./components/HitsPanel/HitsPanel.js";
import { drawMinimap, mountMinimap } from "./components/Minimap/Minimap.js";
import { drawScenePanel, mountScenePanel } from "./components/ScenePanel/ScenePanel.js";
import { isDragEnding, SCROLL_STEP, ScrollView } from "./components/ScrollView/ScrollView.js";
import { drawSettingsButton, mountSettingsButton } from "./components/SettingsButton/SettingsButton.js";
import { shellPlate } from "./components/ShellPlate/ShellPlate.js";

// The hits screen. Like the client's armor page, the page tells the lobby it supports the full screen mode: the
// Flash lobby page then gives the window the whole screen and draws its header and footer over it in the new style
// (not as opaque bars). The space the header and the footer take is given as external paddings, put into the CSS
// variables --external-padding-top/right/bottom/left.
function applyExternalPaddings() {
    const paddings = viewEnv.getExternalPaddingsRem();
    const style = document.documentElement.style;
    style.setProperty("--external-padding-top", `${paddings.top}rem`);
    style.setProperty("--external-padding-right", `${paddings.right}rem`);
    style.setProperty("--external-padding-bottom", `${paddings.bottom}rem`);
    style.setProperty("--external-padding-left", `${paddings.left}rem`);
}

function init() {
    applyExternalPaddings();
    engine.on("self.onPaddingsUpdated", applyExternalPaddings);
    viewEnv.setFullscreenModeSupported(true);
}

if (engine.whenReady) {
    engine.whenReady.then(init);
} else {
    init();
}

// Mouse over the 3D scene, like the client's SceneWrapper: a drag with the left button turns the camera by the
// mouse deltas in pixels, the wheel zooms by a fixed step. The scene shows the grab cursor, the drag one while
// dragging (.sceneInput__down).
const WHEEL_STEP = 600;
const sceneInput = document.querySelector(".sceneInput");
let dragging = false;
let lastX = 0;
let lastY = 0;

function setDragging(isDragging) {
    dragging = isDragging;
    sceneInput.classList.toggle("sceneInput__down", isDragging);
}

function moveSpace(dx, dy, dz) {
    if (window.model) {
        window.model.onMoveSpace({ dx, dy, dz });
    }
}

function setOverScene(isOver3dScene) {
    if (window.model) {
        window.model.onMouseOver3dScene({ isOver3dScene });
    }
}

sceneInput.addEventListener("mousedown", (event) => {
    event.preventDefault();
    if (event.buttons === 1) {
        setDragging(true);
        lastX = event.clientX;
        lastY = event.clientY;
    }
});
sceneInput.addEventListener("mousemove", (event) => {
    event.preventDefault();
    if (!dragging) {
        return;
    }
    const dx = event.clientX - lastX;
    const dy = event.clientY - lastY;
    lastX = event.clientX;
    lastY = event.clientY;
    if (dx || dy) {
        moveSpace(dx, dy, 0);
    }
});
window.addEventListener("mouseup", () => {
    setDragging(false);
});
sceneInput.addEventListener("wheel", (event) => {
    event.preventDefault();
    moveSpace(0, 0, event.deltaY < 0 ? -WHEEL_STEP : WHEEL_STEP);
});
sceneInput.addEventListener("mouseover", () => setOverScene(true));
sceneInput.addEventListener("mouseout", () => {
    setOverScene(false);
    setDragging(false);
});

// Battle selector: the card shows the selected battle, a click opens the list of the session's battles, a click on
// a battle selects it (onSelect in the model), a click elsewhere or Escape closes the list. The data is in
// window.model.battleSelector and the page draws it again on every model change.
const selector = document.querySelector(".battleSelector");
const oldFormatAlert = document.querySelector(".oldFormatAlert");
const selectorCard = selector.querySelector(".battleSelector__card");
const selectorItems = selector.querySelector(".battleSelector__items");
new ScrollView(selector.querySelector(".battleSelector__list"));

function setImage(node, path) {
    node.style.backgroundImage = path ? `url(${path})` : "none";
}

function setSelectorOpen(open) {
    selector.classList.toggle("battleSelector__open", open && !selector.classList.contains("battleSelector__empty"));
}

const RESULT_CLASSES = {
    win: "battleSelector__resultWin",
    defeat: "battleSelector__resultDefeat",
    draw: "battleSelector__resultDraw",
};

// The result after the map name; empty when it is not known.
function setResult(node, battle) {
    node.className = `battleSelector__result ${RESULT_CLASSES[battle.result] || ""}`;
    node.textContent = battle.resultText || "";
}

function titleRow(battle) {
    const row = element("div", "battleSelector__titleRow");
    row.appendChild(element("div", "battleSelector__itemMap", battle.mapName));
    const result = element("div", "");
    setResult(result, battle);
    row.appendChild(result);
    return row;
}

function drawBattleSelector() {
    const model = window.model && window.model.battleSelector;
    if (!model) {
        return;
    }
    const battles = arrayItems(model.battles);
    const selected = battles.find((battle) => battle.id === model.selectedId) || battles[0];
    selector.classList.toggle("battleSelector__empty", !selected);
    oldFormatAlert.classList.toggle("oldFormatAlert__visible", Boolean(selected && selected.isOldFormat));
    oldFormatAlert.querySelector(".oldFormatAlert__text").textContent = model.oldFormatText;
    if (!selected) {
        // No battles yet: the card shows the empty title only.
        setSelectorOpen(false);
        selector.querySelector(".battleSelector__mapName").textContent = model.emptyTitle;
        selectorItems.textContent = "";
        return;
    }
    setImage(selector.querySelector(".battleSelector__mapImage"), selected.mapImage);
    selector.querySelector(".battleSelector__mapName").textContent = selected.mapName;
    setResult(selector.querySelector(".battleSelector__result"), selected);
    selector.querySelector(".battleSelector__vehicle").textContent = selected.vehicleName;
    selector.querySelector(".battleSelector__time").textContent = selected.time;

    // The battles come newest first: a day row starts each day.
    selectorItems.textContent = "";
    let day = null;
    battles.forEach((battle) => {
        if (battle.day !== day) {
            day = battle.day;
            selectorItems.appendChild(element("div", "battleSelector__day", day));
        }
        const item = element("div", "battleSelector__item");
        item.classList.toggle("battleSelector__itemSelected", battle === selected);
        item.appendChild(element("div", "battleSelector__itemBg"));
        const image = element("div", "battleSelector__itemImage");
        setImage(image, battle.mapImage);
        item.appendChild(image);
        const info = element("div", "battleSelector__itemInfo");
        info.appendChild(titleRow(battle));
        info.appendChild(element("div", "battleSelector__line battleSelector__vehicle", battle.vehicleName));
        item.appendChild(info);
        item.appendChild(element("div", "battleSelector__itemTime", battle.time));
        // Handlers keep plain values: the model's items are destroyed when the model is filled again.
        const id = battle.id;
        item.addEventListener("click", (event) => {
            event.stopPropagation();
            setSelectorOpen(false);
            window.model.battleSelector.onSelect({ id });
        });
        selectorItems.appendChild(item);
    });
}

selectorCard.addEventListener("click", (event) => {
    event.stopPropagation();
    setSelectorOpen(!selector.classList.contains("battleSelector__open"));
});
selector.querySelector(".battleSelector__list").addEventListener("click", (event) => event.stopPropagation());
document.addEventListener("click", () => {
    // A thumb dragged out of the list and let go is not a click elsewhere.
    if (!isDragEnding()) {
        setSelectorOpen(false);
    }
});
document.addEventListener("keydown", (event) => {
    if (event.keyCode === 27) {
        setSelectorOpen(false);
    }
});

// Hits panel under the battle selector: a component of its own (components/HitsPanel/), at the end of the left
// column; the minimap (components/Minimap/) at the end of the panel.
mountMinimap(mountHitsPanel(document.querySelector(".hitsView__left")));

// Scene panel at the bottom: a component of its own (components/ScenePanel/), at the end of the content.
mountScenePanel(document.querySelector(".hitsView__content"));

// Settings button right of the battle selector: a component of its own (components/SettingsButton/), at the end
// of the content.
mountSettingsButton(document.querySelector(".hitsView__content"));

// Bug button right of the settings: a component of its own (components/BugButton/), at the end of the content.
mountBugButton(document.querySelector(".hitsView__content"));

// Shot panel: the chosen hit's shooter and target cards, its result, its sections (window.model.shotPanel). A value
// counted in the garage is underlined with dashes.
const shotPanel = document.querySelector(".shotPanel");
const shotVehicles = shotPanel.querySelector(".shotPanel__vehicles");
const shotSections = shotPanel.querySelector(".shotPanel__sections");
// On a low screen the panel does not fit and scrolls, without a bar: the wheel by the scroll views' step and way.
shotPanel.addEventListener("wheel", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.deltaY) {
        const step = viewEnv.remToPx(SCROLL_STEP);
        shotPanel.scrollTop += event.deltaY < 0 ? step : -step;
    }
});

function shotVehicle(vehicle, role) {
    const node = element("div", "shotPanel__vehicle");
    const who = element("div", "shotPanel__who");
    who.appendChild(element("div", "shotPanel__role", vehicle.role));
    who.appendChild(element("div", "shotPanel__player", vehicle.player));
    node.appendChild(who);
    const body = element("div", "shotPanel__body");
    const card = element("div", "shotPanel__card");
    const flag = element("div", "shotPanel__flag");
    setImage(flag, vehicle.flag);
    card.appendChild(flag);
    const icon = element("div", "shotPanel__vehicleIcon");
    setImage(icon, vehicle.icon);
    card.appendChild(icon);
    const caption = element("div", "shotPanel__caption");
    caption.appendChild(element("div", "", vehicle.tier));
    caption.appendChild(element("div", "shotPanel__vehicleName", vehicle.vehicleName));
    card.appendChild(caption);
    body.appendChild(card);
    const modules = element("div", "shotPanel__modules");
    arrayItems(vehicle.modules).forEach((module, index) => {
        const moduleIcon = element("div", "shotPanel__moduleIcon");
        setImage(moduleIcon, module.icon);
        if (module.tier) {
            moduleIcon.appendChild(element("div", "shotPanel__moduleTier", module.tier));
        }
        // The hit's shell mode on the shooter's shell, in the corner the client marks a gun's mechanic in.
        if (module.shellMode) {
            moduleIcon.appendChild(element("div", `shotPanel__shellMode shotPanel__shellMode__${module.shellMode}`));
        }
        // The client's tooltip of the module: HitsView.getTooltipData finds it by the card's role and the index.
        moduleIcon.addEventListener("mouseenter", () => clientTooltip(true, { role, index }));
        moduleIcon.addEventListener("mouseleave", () => clientTooltip(false, { role, index }));
        modules.appendChild(moduleIcon);
    });
    body.appendChild(modules);
    node.appendChild(body);
    return node;
}

// The section icons: the client's damage log icons (the red cross of damage, the yellow one of modules), the armor
// tooltip's (the resulting armor, the impact angle), the mod's for the others.
const SECTION_ICONS = {
    damage: "hitIcon hitIcon__damage__received",
    crits: "hitIcon hitIcon__critical__received",
    penetration: "shotPanel__icon__penetration",
    armor: "shotPanel__icon__armor",
    angle: "shotPanel__icon__angle",
    distance: "shotPanel__icon__distance",
};

function drawShotPanel() {
    const model = window.model && window.model.shotPanel;
    shotPanel.classList.toggle("shotPanel__visible", Boolean(model && model.isVisible));
    if (!model || !model.isVisible) {
        return;
    }
    shotVehicles.innerHTML = "";
    shotVehicles.appendChild(shotVehicle(model.shooter, "shooter"));
    shotVehicles.appendChild(shotVehicle(model.target, "target"));
    shotSections.innerHTML = "";
    arrayItems(model.sections).forEach((section) => {
        const head = element("div", `shotPanel__head shotPanel__head__${section.kind}`);
        // Modules and crew get their accent only when the hit damaged some.
        head.classList.toggle("shotPanel__head__critsDamaged", section.kind === "crits" && section.value !== "0");
        head.appendChild(element("div", `shotPanel__icon ${SECTION_ICONS[section.kind] || ""}`));
        const value = element("div", "shotPanel__value");
        value.appendChild(element("span", section.counted ? "shotPanel__counted" : "", section.value));
        head.appendChild(value);
        const title = element("div", "shotPanel__title", section.title);
        head.appendChild(title);
        // The shell kind on a plate beside the penetration, like in the hits list: gold for a premium shell.
        if (section.kind === "penetration" && model.shellText) {
            head.appendChild(shellPlate(model.shellText, model.isGoldShell, model.isSpgShell, "shotPanel__shell"));
        }
        shotSections.appendChild(head);
        arrayItems(section.rows).forEach((item) => {
            const row = element("div", "shotPanel__row");
            const rowValue = element("div", "shotPanel__rowValue");
            rowValue.appendChild(element("span", item.counted ? "shotPanel__counted" : "", item.value));
            row.appendChild(rowValue);
            row.appendChild(element("div", "shotPanel__rowLabel", item.label));
            shotSections.appendChild(row);
        });
        if (section.kind === "crits") {
            drawDevices(model);
        }
    });
}

// The modules and crew of the crits section, like the battle damage panel: the module kinds in two columns with an
// abstract tank between them, the crew members in a row under a line, in the middle; a cell the panel's icon at its
// state (its color), framed when the shot damaged it, dim when not. The note under it: only this shot's damage.
const DEVICE_LEFT = 0;
const DEVICE_RIGHT = 1;
const DEVICE_CREW = 2;
// In rem: the top of the tank's front wheels, how far below them the rear ones are.
const WHEEL_TOP = 32;
const WHEEL_WAY = 98;

function deviceCells(devices, group, className) {
    const box = element("div", className);
    devices.filter((device) => device.group === group).forEach((device) => {
        const cell = element("div", `shotPanel__deviceCell shotPanel__deviceCell__${device.state}`);
        const icon = element("div", "shotPanel__deviceIcon");
        icon.style.backgroundImage = `url(img://gui/maps/sagtary_armor_hits/modules/${device.icon}.png)`;
        cell.appendChild(icon);
        box.appendChild(cell);
    });
    return box;
}

// The tank from above, the gun forward: its tracks or wheels at the state the shot left them in.
function drawTank(parts) {
    const tank = element("div", "shotPanel__tank");
    parts.forEach((part) => {
        const item = element("div", `shotPanel__tankPart shotPanel__tankPart__${part.name} shotPanel__tankPart__${part.state}`);
        if (part.rowCount > 1) {
            item.style.top = `${WHEEL_TOP + WHEEL_WAY * part.row / (part.rowCount - 1)}rem`;
        }
        tank.appendChild(item);
    });
    tank.appendChild(element("div", "shotPanel__tankPart shotPanel__tankHull"));
    tank.appendChild(element("div", "shotPanel__tankPart shotPanel__tankGun"));
    tank.appendChild(element("div", "shotPanel__tankPart shotPanel__tankTurret"));
    return tank;
}

function drawDevices(model) {
    const devices = arrayItems(model.devices);
    if (!devices.length) {
        return;
    }
    const box = element("div", "shotPanel__devices");
    const vehicle = element("div", "shotPanel__deviceVehicle");
    vehicle.appendChild(deviceCells(devices, DEVICE_LEFT, "shotPanel__deviceColumn"));
    vehicle.appendChild(drawTank(arrayItems(model.tankParts)));
    vehicle.appendChild(deviceCells(devices, DEVICE_RIGHT, "shotPanel__deviceColumn"));
    box.appendChild(vehicle);
    box.appendChild(element("div", "shotPanel__deviceLine"));
    box.appendChild(deviceCells(devices, DEVICE_CREW, "shotPanel__deviceCrew"));
    box.appendChild(element("div", "shotPanel__deviceNote", model.devicesNote));
    shotSections.appendChild(box);
}

function draw() {
    drawBattleSelector();
    drawHitsPanel();
    drawMinimap();
    drawScenePanel();
    drawShotPanel();
    drawSettingsButton();
    drawBugButton();
}

// The page draws again on a change of the model or of any of its parts: a change inside a part (its arrays, its
// selection) is told to the observers of that part's path.
engine.whenReady.then(() => {
    const paths = ["model", "model.battleSelector", "model.hitsPanel", "model.hitsPanel.sides",
        "model.hitsPanel.results", "model.hitsPanel.hits", "model.fileButtons", "model.overlayPanel",
        "model.scenePanel", "model.shotPanel", "model.settingsMenu", "model.modPage", "model.minimap",
        "model.settingsMenu.items", "model.settingsMenu.modes", "model.minimap.vehicles",
        "model.shotPanel.shooter", "model.shotPanel.target", "model.shotPanel.sections", "model.shotPanel.devices",
        "model.shotPanel.tankParts",
        "model.shotPanel.shooter.modules", "model.shotPanel.target.modules"];
    const callbackIDs = paths.map((path) =>
        viewEnv.addDataChangedCallback(path, 0, true),
    );
    engine.on("viewEnv.onDataChanged", (data, indexes, changedIDs) => {
        if (callbackIDs.some((id) => changedIDs.indexOf(id) !== -1)) {
            draw();
        }
    });
    draw();
});
