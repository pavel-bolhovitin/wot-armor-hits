// Hits panel under the battle selector (window.model.hitsPanel): the hits of the selected battle on the player and by
// the player, in one list in the battle's order. The header: the filter, which says what the list shows (all hits or
// the chosen side's mark and name, then the chosen results' icons) and opens its menu; the chosen hit's place among
// the shown ones and the arrows that step through them, up to the one above, down to the one below (onStep). The menu,
// over the list, like the settings menu: the sides, then the results, a check box each with how many hits it has; a
// click on a line goes to the presenter (onSideFilter, onResultFilter), the menu stays open; a click on the filter,
// elsewhere or Escape closes it. A row: the hit's side as a bar and a faint gradient at its left, then its time and the
// order of the client's damage log; a click chooses it (onHit). The presenter fills the model again on every click.
// Its styles are in HitsPanel.css, linked in HitsView.html. The menu, the check box, the scroll view, the hit icons
// and the shell plates are components of their own.
import { element, withChildren } from "../../common/dom.js";
import { arrayItems } from "../../common/model.js";
import { checkBox } from "../CheckBox/CheckBox.js";
import { dropMenu, dropMenuItem } from "../DropMenu/DropMenu.js";
import { classIcon, hitIcon } from "../HitIcon/HitIcon.js";
import { ScrollView } from "../ScrollView/ScrollView.js";
import { shellPlate } from "../ShellPlate/ShellPlate.js";

// Rem a row of the list takes: .hitsPanel__row's height, its frame inside it (Gameface lays boxes out with the
// borders inside the height: the rows are 28 pixels apart on the screen).
const HIT_ROW_REM = 28;

// The nodes the drawing fills, made by mountHitsPanel.
let nodes = null;

function setMenuOpen(open) {
    nodes.root.classList.toggle("hitsPanel__menuOpen", open);
}

function sideMark(side) {
    return element("div", `hitsPanel__sideMark hitsPanel__sideMark__${side}`);
}

// The filter's icon of a result: one for both sides (the damage is the red one).
function resultIcon(result) {
    return hitIcon(result, "received");
}

// Makes the panel at the end of parent and gives its root (the minimap goes at its end); once, before the first
// drawing.
export function mountHitsPanel(parent) {
    const summary = element("div", "hitsPanel__summary");
    const filter = withChildren(element("div", "hitsPanel__filter"), [
        element("div", "hitsPanel__filterIcon"),
        summary,
        element("div", "hitsPanel__caret"),
    ]);
    const position = element("div", "hitsPanel__position");
    const prev = element("div", "hitsPanel__step hitsPanel__prev");
    const next = element("div", "hitsPanel__step hitsPanel__next");
    const header = withChildren(element("div", "hitsPanel__header"), [
        withChildren(element("div", "hitsPanel__filterBox"), [filter]),
        withChildren(element("div", "hitsPanel__nav"), [position, prev, next]),
    ]);
    const sides = element("div", "hitsPanel__menuGroup");
    const results = element("div", "hitsPanel__menuGroup");
    const menu = dropMenu("hitsPanel__menu", [sides, results], () => setMenuOpen(false));
    const items = element("div", "hitsPanel__items");
    const list = withChildren(element("div", "hitsPanel__list scrollView"), [
        withChildren(element("div", "scrollView__content"), [items]),
    ]);
    const root = withChildren(element("div", "hitsPanel"), [header, list, menu]);
    nodes = { root, summary, position, sides, results, items, scroll: new ScrollView(list) };
    filter.addEventListener("click", (event) => {
        event.stopPropagation();
        setMenuOpen(!root.classList.contains("hitsPanel__menuOpen"));
    });
    prev.addEventListener("click", () => window.model.hitsPanel.onStep({ delta: -1 }));
    next.addEventListener("click", () => window.model.hitsPanel.onStep({ delta: 1 }));
    parent.appendChild(root);
    return root;
}

// What the list shows: the side, the label of all hits with 'All' on, else the chosen side's mark and name; then the
// chosen results' icons only, none with 'All' on.
function drawSummary(model, sides, results) {
    const summary = nodes.summary;
    summary.textContent = "";
    const chosenSides = sides.filter((item) => item.id && item.isOn);
    if (!chosenSides.length) {
        summary.appendChild(element("div", "hitsPanel__summaryText", model.allHitsLabel));
    }
    chosenSides.forEach((item) => {
        summary.appendChild(sideMark(item.id));
        summary.appendChild(element("div", "hitsPanel__summaryText", item.label));
    });
    results.filter((item) => item.id && item.isOn).forEach((item) => summary.appendChild(resultIcon(item.id)));
}

// A group of the menu: a line an item, 'All' (its id '') without a mark.
function drawMenuGroup(node, items, mark, onPick) {
    node.textContent = "";
    items.forEach((item) => {
        const row = dropMenuItem("hitsPanel__menuItem", [
            checkBox(item.isOn),
            withChildren(element("div", "hitsPanel__menuMark"), item.id ? [mark(item.id)] : []),
            element("div", "hitsPanel__menuLabel", item.label),
            element("div", "hitsPanel__menuCount", String(item.count)),
        ]);
        row.classList.toggle("hitsPanel__menuItemOn", Boolean(item.isOn));
        // Handlers keep plain values: the model's items are destroyed when the model is filled again.
        const id = item.id;
        row.addEventListener("click", () => onPick(id));
        node.appendChild(row);
    });
}

// The list in columns, each as wide as its widest cell, so a cell wider in one row (a shell kind's text, which differs
// by language) widens its whole column, not its row: Gameface has no tables or grid, a column of cells in a flex row
// sizes to its content. The rows under the columns, as many and as high as their cells, draw the rows' sides and
// frames and take the hover and the clicks: the columns let the mouse through. The vehicle and the player share the
// rest.
function drawList(hits, selectedHit, hasShellModes) {
    const list = nodes.items;
    list.textContent = "";
    const rows = element("div", "hitsPanel__rows");
    const columns = element("div", "hitsPanel__columns");
    list.appendChild(rows);
    list.appendChild(columns);
    const column = (kind) => {
        const node = element("div", `hitsPanel__column hitsPanel__column__${kind}`);
        columns.appendChild(node);
        return node;
    };
    // The order of the client's damage log after the time: damage, result, critical, shell (its mode when a hit of
    // the battle has a known one), class, vehicle; the player last.
    const times = column("time");
    const damages = column("damage");
    const results = column("result");
    const criticals = column("critical");
    const shells = column("shell");
    const shellModes = hasShellModes ? column("shellModes") : null;
    const classes = column("class");
    const vehicles = column("vehicle");
    const players = column("player");
    // A cell of a text, or of an icon or a plate: centered in the row's height, at the column's left.
    const cell = (parent, text, content) => {
        const node = element("div", content ? "hitsPanel__cell hitsPanel__cellBox" : "hitsPanel__cell", text);
        if (content) {
            node.appendChild(content);
        }
        parent.appendChild(node);
        return node;
    };
    hits.forEach((hit, index) => {
        const side = hit.side;
        const isSelected = index === selectedHit;
        const row = withChildren(element("div", `hitsPanel__row hitsPanel__row__${side}`),
            [element("div", "hitsPanel__rowBar")]);
        row.classList.toggle("hitsPanel__rowSelected", isSelected);
        row.addEventListener("click", () => window.model.hitsPanel.onHit({ index }));
        rows.appendChild(row);
        cell(times, hit.time).classList.toggle("hitsPanel__cellSelected", isSelected);
        // No damage when the hit took none.
        cell(damages, hit.damage ? String(hit.damage) : "");
        cell(results, undefined, hitIcon(hit.result, side));
        // The critical icon of a hit that damaged modules or crew.
        const critical = hitIcon("critical", side);
        critical.classList.toggle("hitsPanel__criticalNone", !hit.hasCrits);
        cell(criticals, undefined, critical);
        // The shell plate at the column's left.
        const shell = shellPlate(hit.shellText, hit.isGoldShell, hit.isSpgShell);
        shell.title = hit.shellName;
        cell(shells, undefined, shell);
        // The icon of the shell's mode; none on a row of an unknown mode.
        if (shellModes) {
            cell(shellModes, undefined, element("div", hit.shellMode
                ? `hitsPanel__shellMode hitsPanel__shellMode__${hit.shellMode}` : "hitsPanel__shellMode"));
        }
        cell(classes, undefined, classIcon(hit.vehicleClass));
        cell(vehicles, hit.vehicleName);
        cell(players, hit.playerName);
    });
}

// Draws the panel from the model; on every change of it.
export function drawHitsPanel() {
    if (!nodes) {
        return;
    }
    const model = window.model && window.model.hitsPanel;
    const isVisible = Boolean(model && model.isVisible);
    nodes.root.classList.toggle("hitsPanel__visible", isVisible);
    if (!isVisible) {
        setMenuOpen(false);
        return;
    }
    const sides = arrayItems(model.sides);
    const results = arrayItems(model.results);
    drawSummary(model, sides, results);
    drawMenuGroup(nodes.sides, sides, sideMark, (id) => window.model.hitsPanel.onSideFilter({ id }));
    drawMenuGroup(nodes.results, results, resultIcon, (id) => window.model.hitsPanel.onResultFilter({ id }));

    const hits = arrayItems(model.hits);
    nodes.position.textContent = hits.length ? `${model.selectedHit + 1} / ${hits.length}` : "0 / 0";
    drawList(hits, model.selectedHit, model.hasShellModes);
    // The chosen hit in view (the steps, a filter changed). Its place comes from its index: the rows are all as high,
    // and Gameface lays the new rows out a few frames later.
    if (model.selectedHit >= 0 && model.selectedHit < hits.length) {
        const rowHeight = viewEnv.remToPx(HIT_ROW_REM);
        nodes.scroll.reveal(model.selectedHit * rowHeight, rowHeight);
    }
}
