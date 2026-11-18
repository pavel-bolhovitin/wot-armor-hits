// Settings button right of the battle selector: the gear opens the menu of the mod's settings below it
// (window.model.settingsMenu): a setting a row, on or off, a click turns it over (onToggle); how the battles of each
// group of modes are kept, a row a group, its name and three choices: off, for the session, in files too
// (onBattleMode). Under them the file buttons (window.model.fileButtons), an icon and a label each: save the chosen
// battle to its file (a disk; off without a battle), delete all the battles (a bin; off without battles), which asks
// first: the question and its two choices in its place, until a choice or the menu closes. A click elsewhere or Escape
// closes the menu.
// Its styles are in SettingsButton.css, linked in HitsView.html; the menu and the check box are components of their
// own (components/DropMenu/, components/CheckBox/).
import { element, withChildren } from "../../common/dom.js";
import { arrayItems } from "../../common/model.js";
import { checkBox } from "../CheckBox/CheckBox.js";
import { dropMenu, dropMenuItem } from "../DropMenu/DropMenu.js";

// The nodes the drawing fills, made by mountSettingsButton.
let nodes = null;
let isDeleteAsked = false;

function setDeleteAsked(asked) {
    isDeleteAsked = asked;
    nodes.files.classList.toggle("fileButtons__asking", asked);
}

function setOpen(open) {
    nodes.root.classList.toggle("settingsButton__open", open);
    if (!open) {
        setDeleteAsked(false);
    }
}

// A file button: its icon drawn of parts, then its label.
function createFileButton(kind, iconParts, label) {
    const icon = withChildren(element("div", "fileButtons__icon"),
        iconParts.map((part) => element("div", `fileButtons__${part}`)));
    return withChildren(element("div", `fileButtons__button fileButtons__${kind}`), [icon, label]);
}

function createFileButtons() {
    const saveLabel = element("div", "fileButtons__label");
    const deleteLabel = element("div", "fileButtons__label");
    const save = createFileButton("save", ["disk", "diskShutter", "diskLabel"], saveLabel);
    const remove = createFileButton("delete", ["binLid", "binHandle", "binBody"], deleteLabel);
    const confirmText = element("div", "fileButtons__confirmText");
    const confirmDelete = element("div", "fileButtons__choice fileButtons__choiceDelete");
    const confirmCancel = element("div", "fileButtons__choice fileButtons__choiceCancel");
    const files = withChildren(element("div", "fileButtons"), [
        save,
        remove,
        withChildren(element("div", "fileButtons__confirm"), [
            confirmText,
            withChildren(element("div", "fileButtons__choices"), [confirmDelete, confirmCancel]),
        ]),
    ]);
    save.addEventListener("click", () => window.model.fileButtons.onSave());
    remove.addEventListener("click", () => setDeleteAsked(true));
    confirmDelete.addEventListener("click", () => {
        setDeleteAsked(false);
        window.model.fileButtons.onDelete();
    });
    confirmCancel.addEventListener("click", () => setDeleteAsked(false));
    return { files, save, remove, saveLabel, deleteLabel, confirmText, confirmDelete, confirmCancel };
}

// Makes the button at the end of parent; once, before the first drawing.
export function mountSettingsButton(parent) {
    const title = element("div", "settingsMenu__title");
    const items = element("div", "settingsMenu__items");
    const modesTitle = element("div", "settingsMenu__modesTitle");
    const modeRows = element("div", "settingsMenu__modeRows");
    const fileNodes = createFileButtons();
    const menu = dropMenu("settingsMenu", [
        title,
        items,
        withChildren(element("div", "settingsMenu__modes"), [modesTitle, modeRows]),
        fileNodes.files,
    ], () => setOpen(false));
    const root = withChildren(element("div", "settingsButton"), [element("div", "settingsButton__icon"), menu]);
    nodes = Object.assign({ root, title, items, modesTitle, modeRows }, fileNodes);
    root.addEventListener("click", (event) => {
        event.stopPropagation();
        setOpen(!root.classList.contains("settingsButton__open"));
    });
    parent.appendChild(root);
}

function drawSettings(model) {
    nodes.title.textContent = model.title;
    nodes.items.textContent = "";
    arrayItems(model.items).forEach((item) => {
        const row = dropMenuItem("settingsMenu__item", [checkBox(item.isOn, "settingsMenu__box")]);
        row.classList.toggle("settingsMenu__itemOn", Boolean(item.isOn));
        const text = withChildren(element("div", "settingsMenu__text"), [
            element("div", "settingsMenu__label", item.label),
        ]);
        if (item.note) {
            text.appendChild(element("div", "settingsMenu__note", item.note));
        }
        row.appendChild(text);
        // Handlers keep plain values: the model's items are destroyed when the model is filled again.
        const key = item.key;
        row.addEventListener("click", () => window.model.settingsMenu.onToggle({ key }));
        nodes.items.appendChild(row);
    });

    nodes.modesTitle.textContent = model.modesTitle;
    const savings = [["off", model.offLabel], ["session", model.sessionLabel], ["file", model.fileLabel]];
    nodes.modeRows.textContent = "";
    arrayItems(model.modes).forEach((mode) => {
        const choices = element("div", "settingsMenu__choices");
        const group = mode.group;
        savings.forEach(([saving, label]) => {
            const choice = element("div", "settingsMenu__choice", label);
            choice.classList.toggle("settingsMenu__choiceSelected", saving === mode.saving);
            choice.addEventListener("click", () => window.model.settingsMenu.onBattleMode({ group, saving }));
            choices.appendChild(choice);
        });
        nodes.modeRows.appendChild(withChildren(element("div", "settingsMenu__mode"), [
            element("div", "settingsMenu__modeLabel", mode.label),
            choices,
        ]));
    });
}

// The file buttons are there only with their model.
function drawFileButtons(model) {
    nodes.files.classList.toggle("fileButtons__visible", Boolean(model));
    nodes.save.classList.toggle("fileButtons__disabled", !(model && model.canSave));
    nodes.remove.classList.toggle("fileButtons__disabled", !(model && model.canDelete));
    nodes.saveLabel.textContent = model ? model.saveLabel : "";
    nodes.deleteLabel.textContent = model ? model.deleteLabel : "";
    nodes.confirmText.textContent = model ? model.confirmText : "";
    nodes.confirmDelete.textContent = model ? model.confirmLabel : "";
    nodes.confirmCancel.textContent = model ? model.cancelLabel : "";
    if (isDeleteAsked && !(model && model.canDelete)) {
        setDeleteAsked(false);
    }
}

// Draws the menu and the file buttons from the model; on every change of it.
export function drawSettingsButton() {
    if (!nodes) {
        return;
    }
    const model = window.model;
    if (model && model.settingsMenu) {
        drawSettings(model.settingsMenu);
    }
    drawFileButtons(model && model.fileButtons);
}
