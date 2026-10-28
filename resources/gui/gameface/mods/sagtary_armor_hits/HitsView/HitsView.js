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
// Scroll view: a list (.scrollView__content, its rows in one block) that scrolls in its box (.scrollView) with a bar
// right of it, like the client's barracks list (its VerticalScroll): arrows at the ends, the thumb on a rail, the
// client's images. Gameface draws no bar of its own. The page scrolls the list itself: the wheel and the arrows a part
// of the visible height a step (Gameface's own wheel step is a few pixels), a click on the rail a page, the thumb
// follows a drag. Gameface gives a negative deltaY for the wheel turned towards the user (down). The bar shows only
// when the list does not fit.
// It follows the sizes, as the client's scroll does (useRefResizeObserver): of the visible list (shown, hidden, the
// window resized) and of its rows (filled again); Gameface lays a list out a few frames after it changes.
const LIST_STEP = 0.3;
// A drag of a thumb that ended this long ago in ms is still ending: the click it makes is not a click elsewhere.
const DRAG_CLICK_MS = 300;
let dragEndedAt = 0;

function isDragEnding() {
    return Date.now() - dragEndedAt < DRAG_CLICK_MS;
}

class ScrollView {
    constructor(root) {
        this.root = root;
        this.content = root.querySelector(".scrollView__content");
        const bar = element("div", "scrollView__bar");
        this.up = element("div", "scrollView__button scrollView__up");
        this.track = element("div", "scrollView__track");
        this.track.appendChild(element("div", "scrollView__rail"));
        this.thumb = element("div", "scrollView__thumb");
        this.track.appendChild(this.thumb);
        this.down = element("div", "scrollView__button scrollView__down");
        bar.appendChild(this.up);
        bar.appendChild(this.track);
        bar.appendChild(this.down);
        root.appendChild(bar);
        // {y, scrollTop} where the thumb's drag started, null without a drag.
        this.drag = null;

        root.addEventListener("wheel", (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (event.deltaY) {
                this.scrollBy(event.deltaY < 0 ? this.step() : -this.step());
            }
        });
        this.up.addEventListener("click", () => this.scrollBy(-this.step()));
        this.down.addEventListener("click", () => this.scrollBy(this.step()));
        this.track.addEventListener("click", (event) => {
            if (event.target === this.thumb || isDragEnding()) {
                return;
            }
            const page = this.content.clientHeight;
            this.scrollBy(event.clientY < this.thumb.getBoundingClientRect().top ? -page : page);
        });
        this.thumb.addEventListener("mousedown", (event) => {
            event.preventDefault();
            event.stopPropagation();
            this.drag = { y: event.clientY, scrollTop: this.content.scrollTop };
        });
        window.addEventListener("mousemove", (event) => {
            if (!this.drag) {
                return;
            }
            const free = this.track.clientHeight - this.thumb.offsetHeight;
            if (free > 0) {
                this.content.scrollTop = this.drag.scrollTop + ((event.clientY - this.drag.y) * this.range()) / free;
                this.update();
            }
        });
        window.addEventListener("mouseup", () => {
            if (this.drag) {
                this.drag = null;
                dragEndedAt = Date.now();
            }
        });
        this.content.addEventListener("scroll", () => this.update());
        const observer = new ResizeObserver(() => this.update());
        observer.observe(this.content);
        observer.observe(this.content.firstElementChild);
    }

    range() {
        return this.content.scrollHeight - this.content.clientHeight;
    }

    step() {
        return Math.max(40, this.content.clientHeight * LIST_STEP);
    }

    scrollBy(delta) {
        this.content.scrollTop += delta;
        this.update();
    }

    // Scrolls the least so that the part of the list from top, height high (pixels), is in view.
    reveal(top, height) {
        const content = this.content;
        const view = content.clientHeight;
        if (!view) {
            return;
        }
        if (top < content.scrollTop) {
            content.scrollTop = top;
        } else if (top + height > content.scrollTop + view) {
            content.scrollTop = top + height - view;
        }
        this.update();
    }

    update() {
        const content = this.content;
        const range = this.range();
        const scrolls = range > 1;
        this.root.classList.toggle("scrollView__scrolls", scrolls);
        if (!scrolls) {
            return;
        }
        this.thumb.style.height = `${(100 * content.clientHeight) / content.scrollHeight}%`;
        const free = Math.max(0, this.track.clientHeight - this.thumb.offsetHeight);
        this.thumb.style.top = `${free * Math.min(1, content.scrollTop / range)}px`;
        this.up.classList.toggle("scrollView__buttonOff", content.scrollTop <= 0);
        this.down.classList.toggle("scrollView__buttonOff", content.scrollTop >= range - 1);
    }
}

sceneInput.addEventListener("mouseover", () => setOverScene(true));
sceneInput.addEventListener("mouseout", () => {
    setOverScene(false);
    setDragging(false);
});

// Battle selector: the card shows the selected battle, a click opens the list of the session's battles, a click on
// a battle selects it (onSelect in the model), a click elsewhere or Escape closes the list. The data is in
// window.model.battleSelector and the page draws it again on every model change.
const selector = document.querySelector(".battleSelector");
const selectorCard = selector.querySelector(".battleSelector__card");
const selectorItems = selector.querySelector(".battleSelector__items");
new ScrollView(selector.querySelector(".battleSelector__list"));

// Array items of a view model may come wrapped as {value: item}.
function arrayItems(array) {
    const items = [];
    for (let index = 0; array && index < array.length; index++) {
        const item = array[index];
        items.push(item && item.value !== undefined ? item.value : item);
    }
    return items;
}

function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) {
        node.textContent = text;
    }
    return node;
}

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

// Hits panel: tabs (received or dealt hits), result filters, the chosen hit and the list
// (window.model.hitsPanel). Every click goes to the presenter, which fills the model again.
const hitsPanel = document.querySelector(".hitsPanel");
const hitsFilters = hitsPanel.querySelector(".hitsPanel__filters");
const hitsList = hitsPanel.querySelector(".hitsPanel__items");
const hitsScroll = new ScrollView(hitsPanel.querySelector(".hitsPanel__list"));
// Rem a row of the list takes: .hitsPanel__row's height, its top border inside it (Gameface lays boxes out with the
// borders inside the height: the rows are 28 pixels apart on the screen).
const HIT_ROW_REM = 28;

function hitIcon(kind, side) {
    return element("div", `hitIcon hitIcon__${kind}__${side}`);
}


function chip(selected, onClick) {
    const node = element("div", "hitsPanel__chip");
    node.classList.toggle("hitsPanel__chipSelected", selected);
    node.addEventListener("click", onClick);
    return node;
}

function drawHitsPanel() {
    const model = window.model && window.model.hitsPanel;
    hitsPanel.classList.toggle("hitsPanel__visible", Boolean(model && model.isVisible));
    if (!model || !model.isVisible) {
        return;
    }
    const side = model.side;
    hitsPanel.querySelectorAll(".hitsPanel__tab").forEach((tab) => {
        const tabSide = tab.getAttribute("data-side");
        tab.textContent = tabSide === "received" ? model.receivedLabel : model.dealtLabel;
        tab.classList.toggle("hitsPanel__tabSelected", tabSide === side);
    });

    hitsFilters.textContent = "";
    arrayItems(model.filters).forEach((filter) => {
        const id = filter.id;
        const node = chip(id === model.selectedFilter, () => window.model.hitsPanel.onFilter({ id }));
        if (id) {
            node.appendChild(hitIcon(id, side));
        } else {
            node.appendChild(document.createTextNode(model.allLabel));
        }
        node.appendChild(element("span", "hitsPanel__count", String(filter.count)));
        hitsFilters.appendChild(node);
    });

    const hits = arrayItems(model.hits);
    hitsPanel.querySelector(".hitsPanel__position").textContent = hits.length
        ? `${model.selectedHit + 1} / ${hits.length}`
        : "0 / 0";
    hitsList.textContent = "";
    hits.forEach((hit, index) => {
        const row = element("div", "hitsPanel__row");
        row.classList.toggle("hitsPanel__rowSelected", index === model.selectedHit);
        row.appendChild(element("div", "hitsPanel__number", String(hit.number)));
        row.appendChild(element("div", "hitsPanel__time", hit.time));
        // Then the order of the client's damage log: damage (none when the hit took none), result, shell, class,
        // vehicle; the player last.
        row.appendChild(element("div", "hitsPanel__damage", hit.damage ? String(hit.damage) : ""));
        row.appendChild(hitIcon(hit.result, side));
        // The critical icon of a hit that damaged modules or crew; its place is kept on the others, so the columns
        // stay in line.
        const critical = hitIcon("critical", side);
        critical.classList.toggle("hitsPanel__criticalNone", !hit.hasCrits);
        row.appendChild(critical);
        const shell = element("div", "hitsPanel__shell", hit.shellText);
        shell.classList.toggle("hitsPanel__shellNone", !hit.shellText);
        shell.classList.toggle("hitsPanel__shellGold", Boolean(hit.isGoldShell));
        shell.title = hit.shellName;
        row.appendChild(shell);
        row.appendChild(element("div", hit.vehicleClass ? `hitIcon hitIcon__class__${hit.vehicleClass}` : "hitIcon"));
        row.appendChild(element("div", "hitsPanel__vehicle", hit.vehicleName));
        row.appendChild(element("div", "hitsPanel__player", hit.playerName));
        row.addEventListener("click", () => window.model.hitsPanel.onHit({ index }));
        hitsList.appendChild(row);
    });
    // The selected hit in view (the steps, a hit chosen elsewhere). Its place comes from its number: the rows are all
    // as high, and Gameface lays the new rows out a few frames later.
    if (model.selectedHit >= 0 && model.selectedHit < hits.length) {
        const rowHeight = viewEnv.remToPx(HIT_ROW_REM);
        hitsScroll.reveal(model.selectedHit * rowHeight, rowHeight);
    }
}

hitsPanel.querySelectorAll(".hitsPanel__tab").forEach((tab) => {
    tab.addEventListener("click", () => window.model.hitsPanel.onSide({ side: tab.getAttribute("data-side") }));
});
hitsPanel.querySelector(".hitsPanel__prev").addEventListener("click", () => window.model.hitsPanel.onStep({ delta: -1 }));
hitsPanel.querySelector(".hitsPanel__next").addEventListener("click", () => window.model.hitsPanel.onStep({ delta: 1 }));

// File buttons: save the chosen battle to its file, delete all the battles (window.model.fileButtons); the save is off
// without a battle, the delete without battles. The delete asks first: the question and its two choices in its place,
// until a choice or the menu closes.
const fileButtons = document.querySelector(".fileButtons");
let isDeleteAsked = false;

function setDeleteAsked(asked) {
    isDeleteAsked = asked;
    fileButtons.classList.toggle("fileButtons__asking", asked);
}

function drawFileButtons() {
    const model = window.model && window.model.fileButtons;
    fileButtons.classList.toggle("fileButtons__visible", Boolean(model));
    fileSave.classList.toggle("fileButtons__disabled", !(model && model.canSave));
    fileDelete.classList.toggle("fileButtons__disabled", !(model && model.canDelete));
    fileButtons.querySelector(".fileButtons__saveLabel").textContent = model ? model.saveLabel : "";
    fileButtons.querySelector(".fileButtons__deleteLabel").textContent = model ? model.deleteLabel : "";
    fileButtons.querySelector(".fileButtons__confirmText").textContent = model ? model.confirmText : "";
    fileButtons.querySelector(".fileButtons__choiceDelete").textContent = model ? model.confirmLabel : "";
    fileButtons.querySelector(".fileButtons__choiceCancel").textContent = model ? model.cancelLabel : "";
    if (isDeleteAsked && !(model && model.canDelete)) {
        setDeleteAsked(false);
    }
}

const fileSave = fileButtons.querySelector(".fileButtons__save");
fileSave.addEventListener("click", () => window.model.fileButtons.onSave());
const fileDelete = fileButtons.querySelector(".fileButtons__delete");
fileDelete.addEventListener("click", () => setDeleteAsked(true));
fileButtons.querySelector(".fileButtons__choiceDelete").addEventListener("click", () => {
    setDeleteAsked(false);
    window.model.fileButtons.onDelete();
});
fileButtons.querySelector(".fileButtons__choiceCancel").addEventListener("click", () => setDeleteAsked(false));

// Overlay panel: the overlay type dropdown (window.model.overlayPanel). A click on
// the dropdown opens its list, a click on a type chooses it (onSelect), a click elsewhere or Escape closes the list.
const overlayPanel = document.querySelector(".overlayPanel");
const overlayDropdown = overlayPanel.querySelector(".overlayPanel__dropdown");
const overlayList = overlayPanel.querySelector(".overlayPanel__list");

function setOverlayOpen(open) {
    overlayDropdown.classList.toggle("overlayPanel__open", open);
}

function drawOverlayPanel() {
    const model = window.model && window.model.overlayPanel;
    if (!model) {
        return;
    }
    overlayPanel.querySelector(".overlayPanel__title").textContent = model.title;
    const selectedId = model.selectedId;
    const items = arrayItems(model.items);
    const selected = items.filter((item) => item.id === selectedId)[0];
    overlayPanel.querySelector(".overlayPanel__selected").textContent = selected ? selected.label : "";
    overlayList.innerHTML = "";
    items.forEach((item) => {
        const row = element("div", `overlayPanel__item${item.id === selectedId ? " overlayPanel__itemSelected" : ""}`);
        row.appendChild(element("div", "overlayPanel__itemBg"));
        row.appendChild(element("div", "overlayPanel__itemLabel", item.label));
        // Handlers keep plain values: the model's items are destroyed when the model is filled again.
        const id = item.id;
        row.addEventListener("click", (event) => {
            event.stopPropagation();
            setOverlayOpen(false);
            window.model.overlayPanel.onSelect({ id });
        });
        overlayList.appendChild(row);
    });
}

overlayPanel.querySelector(".overlayPanel__trigger").addEventListener("click", (event) => {
    event.stopPropagation();
    setOverlayOpen(!overlayDropdown.classList.contains("overlayPanel__open"));
});
document.addEventListener("click", () => setOverlayOpen(false));
document.addEventListener("keydown", (event) => {
    if (event.keyCode === 27) {
        setOverlayOpen(false);
    }
});

// Scene panel: the lines group (a check box: the lines of all the shown hits or of the chosen one, onLines), the camera
// group (the shooter view's check box, onShooterView; the reset, onResetCamera), from window.model.scenePanel.
const scenePanel = document.querySelector(".scenePanel");
const sceneAllLines = scenePanel.querySelector(".scenePanel__allLines");
const sceneShooter = scenePanel.querySelector(".scenePanel__shooter");
const sceneReset = scenePanel.querySelector(".scenePanel__reset");

function drawScenePanel() {
    const model = window.model && window.model.scenePanel;
    if (!model) {
        return;
    }
    scenePanel.querySelector(".scenePanel__linesTitle").textContent = model.linesTitle;
    scenePanel.querySelector(".scenePanel__allLabel").textContent = model.allLabel;
    scenePanel.querySelector(".scenePanel__cameraTitle").textContent = model.cameraTitle;
    scenePanel.querySelector(".scenePanel__shooterLabel").textContent = model.shooterLabel;
    scenePanel.querySelector(".scenePanel__resetLabel").textContent = model.resetLabel;
    sceneAllLines.classList.toggle("scenePanel__checkOn", Boolean(model.allLines));
    sceneShooter.classList.toggle("scenePanel__checkOn", Boolean(model.shooterView));
    // On the dealt side only the chosen hit's line is drawn: no lines group.
    scenePanel.classList.toggle("scenePanel__oneLine", !model.allLinesEnabled);
}

sceneAllLines.addEventListener("click", () =>
    window.model.scenePanel.onLines({ all: !window.model.scenePanel.allLines }));
sceneShooter.addEventListener("click", () => window.model.scenePanel.onShooterView());
sceneReset.addEventListener("click", () => window.model.scenePanel.onResetCamera());

// Settings menu: the gear right of the battle selector opens it, a click on a setting turns it over (onToggle), a click
// on a choice of a group of modes sets how its battles are kept (onBattleMode), a click elsewhere or Escape closes it
// (window.model.settingsMenu).
const settingsButton = document.querySelector(".settingsButton");
const settingsMenu = settingsButton.querySelector(".settingsMenu");
const settingsItems = settingsMenu.querySelector(".settingsMenu__items");
const settingsModes = settingsMenu.querySelector(".settingsMenu__modeRows");

function setSettingsOpen(open) {
    settingsButton.classList.toggle("settingsButton__open", open);
    if (!open) {
        setDeleteAsked(false);
    }
}

function drawSettingsMenu() {
    const model = window.model && window.model.settingsMenu;
    if (!model) {
        return;
    }
    settingsMenu.querySelector(".settingsMenu__title").textContent = model.title;
    settingsItems.textContent = "";
    arrayItems(model.items).forEach((item) => {
        const row = element("div", "settingsMenu__item");
        row.classList.toggle("settingsMenu__itemOn", Boolean(item.isOn));
        const box = element("div", "settingsMenu__box");
        box.appendChild(element("div", "settingsMenu__check"));
        row.appendChild(box);
        const textBox = element("div", "settingsMenu__text");
        textBox.appendChild(element("div", "settingsMenu__label", item.label));
        if (item.note) {
            textBox.appendChild(element("div", "settingsMenu__note", item.note));
        }
        row.appendChild(textBox);
        // Handlers keep plain values: the model's items are destroyed when the model is filled again.
        const key = item.key;
        row.addEventListener("click", () => window.model.settingsMenu.onToggle({ key }));
        settingsItems.appendChild(row);
    });

    settingsMenu.querySelector(".settingsMenu__modesTitle").textContent = model.modesTitle;
    const savings = [["off", model.offLabel], ["session", model.sessionLabel], ["file", model.fileLabel]];
    settingsModes.textContent = "";
    arrayItems(model.modes).forEach((mode) => {
        const row = element("div", "settingsMenu__mode");
        row.appendChild(element("div", "settingsMenu__modeLabel", mode.label));
        const choices = element("div", "settingsMenu__choices");
        const group = mode.group;
        savings.forEach(([saving, label]) => {
            const choice = element("div", "settingsMenu__choice", label);
            choice.classList.toggle("settingsMenu__choiceSelected", saving === mode.saving);
            choice.addEventListener("click", () => window.model.settingsMenu.onBattleMode({ group, saving }));
            choices.appendChild(choice);
        });
        row.appendChild(choices);
        settingsModes.appendChild(row);
    });
}

settingsButton.addEventListener("click", (event) => {
    event.stopPropagation();
    setSettingsOpen(!settingsButton.classList.contains("settingsButton__open"));
});
settingsMenu.addEventListener("click", (event) => event.stopPropagation());
document.addEventListener("click", () => setSettingsOpen(false));
document.addEventListener("keydown", (event) => {
    if (event.keyCode === 27) {
        setSettingsOpen(false);
    }
});

// Shot panel: the chosen hit's shooter and target cards, its result, its sections (window.model.shotPanel). A value
// counted in the garage is underlined with dashes.
const shotPanel = document.querySelector(".shotPanel");
const shotVehicles = shotPanel.querySelector(".shotPanel__vehicles");
const shotSections = shotPanel.querySelector(".shotPanel__sections");

// The client's tooltip of a card's module (a backport tooltip; HitsView.getTooltipData finds it by the role and the
// index), shown and hidden like the client's pages do (a view event, as OpenWG Gameface's libs/views.js sends).
function moduleTooltip(on, role, index) {
    const model = window.model.shotPanel;
    const event = {
        __Type: "GFViewEventProxy",
        type: 1,
        contentID: model.tooltipContentId,
        decoratorID: model.tooltipDecoratorId,
        targetID: 0,
        on: on,
    };
    if (on) {
        event.isMouseEvent = true;
        event.arguments = [
            { __Type: "GFValueProxy", name: "role", string: role },
            { __Type: "GFValueProxy", name: "index", number: index },
        ];
    }
    viewEnv.handleViewEvent(event);
}

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
        moduleIcon.addEventListener("mouseenter", () => moduleTooltip(true, role, index));
        moduleIcon.addEventListener("mouseleave", () => moduleTooltip(false, role, index));
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
            const plate = element("div", "hitsPanel__shell shotPanel__shell", model.shellText);
            plate.classList.toggle("hitsPanel__shellGold", Boolean(model.isGoldShell));
            head.appendChild(plate);
        }
        shotSections.appendChild(head);
        if (section.kind === "crits") {
            drawDevices(model);
        }
        arrayItems(section.rows).forEach((item) => {
            const row = element("div", "shotPanel__row");
            const rowValue = element("div", "shotPanel__rowValue");
            rowValue.appendChild(element("span", item.counted ? "shotPanel__counted" : "", item.value));
            row.appendChild(rowValue);
            row.appendChild(element("div", "shotPanel__rowLabel", item.label));
            shotSections.appendChild(row);
        });
    });
}

// The modules and crew the shot damaged, in the crits section: the modules, then the crew under a line; two cells a
// row, in a cell the battle damage panel's icon (its color tells the state) and the names right of it, a line each,
// both at the top.
function deviceBlock(devices) {
    const box = element("div", "shotPanel__devices");
    devices.forEach((device) => {
        const cell = element("div", "shotPanel__deviceCell");
        const icon = element("div", "shotPanel__deviceIcon");
        icon.style.backgroundImage = `url(img://gui/maps/sagtary_armor_hits/modules/${device.icon}.png)`;
        cell.appendChild(icon);
        const names = element("div", "shotPanel__deviceNames");
        device.text.split("\n").forEach((name) => names.appendChild(element("div", "shotPanel__deviceName", name)));
        cell.appendChild(names);
        box.appendChild(cell);
    });
    shotSections.appendChild(box);
}

function drawDevices(model) {
    const devices = arrayItems(model.devices);
    const modules = devices.filter((device) => !device.isCrew);
    const crew = devices.filter((device) => device.isCrew);
    if (modules.length) {
        deviceBlock(modules);
    }
    if (modules.length && crew.length) {
        shotSections.appendChild(element("div", "shotPanel__deviceLine"));
    }
    if (crew.length) {
        deviceBlock(crew);
    }
}

function draw() {
    drawBattleSelector();
    drawHitsPanel();
    drawFileButtons();
    drawOverlayPanel();
    drawScenePanel();
    drawShotPanel();
    drawSettingsMenu();
}

// The page draws again on a change of the model or of any of its parts: a change inside a part (its arrays, its
// selection) is told to the observers of that part's path.
engine.whenReady.then(() => {
    const paths = ["model", "model.battleSelector", "model.hitsPanel", "model.fileButtons", "model.overlayPanel",
        "model.scenePanel", "model.shotPanel", "model.settingsMenu", "model.settingsMenu.items", "model.settingsMenu.modes",
        "model.shotPanel.shooter", "model.shotPanel.target", "model.shotPanel.sections", "model.shotPanel.devices",
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
