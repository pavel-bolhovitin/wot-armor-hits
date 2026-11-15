// Scene panel at the bottom of the hits screen, in the middle of the scene, one row on one plate:
// - the overlay select, the overlay type (window.model.overlayPanel): a click on it opens its list above it, the title
//   of the armor page's menu over the types; a click on a type chooses it (onSelect), a click elsewhere or Escape
//   closes the list; it has no tooltip;
// - a short line;
// - the toggles of the lines of all the shown hits (onLines; none on the dealt side, where only the chosen hit's line
//   is drawn) and of the shooter view (onShooterView), the camera's reset (onResetCamera), from window.model.scenePanel:
//   icons, their names in the client's tooltips (the scene role and the control's id).
// Its styles are in ScenePanel.css, linked in HitsView.html.
import { element, withChildren } from "../../common/dom.js";
import { arrayItems } from "../../common/model.js";
import { clientTooltip } from "../../common/tooltip.js";

const ESCAPE = 27;

// The nodes the drawing fills, made by mountScenePanel.
let nodes = null;

function setOverlayOpen(open) {
    nodes.select.classList.toggle("overlaySelect__open", open);
}

function createOverlaySelect() {
    const select = element("div", "overlaySelect");
    const trigger = withChildren(element("div", "overlaySelect__trigger"), [
        element("div", "overlaySelect__icon"),
        element("div", "overlaySelect__selected"),
        element("div", "overlaySelect__arrow"),
    ]);
    const list = withChildren(element("div", "overlaySelect__list"), [
        element("div", "overlaySelect__title"),
        element("div", "overlaySelect__items"),
    ]);
    trigger.addEventListener("click", (event) => {
        event.stopPropagation();
        setOverlayOpen(!select.classList.contains("overlaySelect__open"));
    });
    list.addEventListener("click", (event) => event.stopPropagation());
    return withChildren(select, [trigger, list]);
}

// A button of an icon, its kind its id for the tooltip; a toggle has a line under it, of its icon's color.
function createButton(kind, toggle) {
    const button = element("div", `scenePanel__button scenePanel__${kind}`);
    button.appendChild(element("div", "scenePanel__icon"));
    if (toggle) {
        button.appendChild(element("div", "scenePanel__line"));
    }
    button.addEventListener("mouseenter", () => clientTooltip(true, { role: "scene", id: kind }));
    button.addEventListener("mouseleave", () => clientTooltip(false, { role: "scene", id: kind }));
    return button;
}

// Makes the panel at the end of parent; once, before the first drawing.
export function mountScenePanel(parent) {
    const select = createOverlaySelect();
    const lines = createButton("lines", true);
    const shooter = createButton("shooter", true);
    const reset = createButton("reset", false);
    const panel = withChildren(element("div", "scenePanel"), [
        select, element("div", "scenePanel__divider"), lines, shooter, reset,
    ]);
    nodes = {
        panel,
        select,
        selected: select.querySelector(".overlaySelect__selected"),
        title: select.querySelector(".overlaySelect__title"),
        items: select.querySelector(".overlaySelect__items"),
        lines,
        shooter,
    };
    lines.addEventListener("click", () =>
        window.model.scenePanel.onLines({ all: !window.model.scenePanel.allLines }));
    shooter.addEventListener("click", () => window.model.scenePanel.onShooterView());
    reset.addEventListener("click", () => window.model.scenePanel.onResetCamera());
    document.addEventListener("click", () => setOverlayOpen(false));
    document.addEventListener("keydown", (event) => {
        if (event.keyCode === ESCAPE) {
            setOverlayOpen(false);
        }
    });
    parent.appendChild(panel);
}

function drawOverlaySelect(model) {
    nodes.title.textContent = model.title;
    const selectedId = model.selectedId;
    const items = arrayItems(model.items);
    const selected = items.filter((item) => item.id === selectedId)[0];
    nodes.selected.textContent = selected ? selected.label : "";
    nodes.items.textContent = "";
    items.forEach((item) => {
        const row = element("div", `overlaySelect__item${item.id === selectedId ? " overlaySelect__itemSelected" : ""}`,
            item.label);
        // Handlers keep plain values: the model's items are destroyed when the model is filled again.
        const id = item.id;
        row.addEventListener("click", (event) => {
            event.stopPropagation();
            setOverlayOpen(false);
            window.model.overlayPanel.onSelect({ id });
        });
        nodes.items.appendChild(row);
    });
}

function drawToggles(model) {
    nodes.lines.classList.toggle("scenePanel__toggleOn", Boolean(model.allLines));
    nodes.shooter.classList.toggle("scenePanel__toggleOn", Boolean(model.shooterView));
    // On the dealt side only the chosen hit's line is drawn: no lines toggle.
    nodes.panel.classList.toggle("scenePanel__oneLine", !model.allLinesEnabled);
}

// Draws the panel from the model; on every change of it.
export function drawScenePanel() {
    const model = window.model;
    if (!nodes || !model) {
        return;
    }
    if (model.overlayPanel) {
        drawOverlaySelect(model.overlayPanel);
    }
    if (model.scenePanel) {
        drawToggles(model.scenePanel);
    }
}
