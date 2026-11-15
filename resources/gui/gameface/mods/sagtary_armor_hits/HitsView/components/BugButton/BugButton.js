// Bug button right of the settings: the red bug opens the card of the mod page below it (window.model.modPage): a line
// with the bug (the links for bugs and ideas are on the mod page), a line with the like (the like button is there too),
// and the button that opens the page in the browser (onOpen), its domain under its label. That click closes the card,
// a click anywhere else or Escape closes it. The other panels stop their clicks, so the card watches the clicks before
// they reach them.
// Its styles are in BugButton.css, linked in HitsView.html.
import { element, withChildren } from "../../common/dom.js";

const ESCAPE = 27;

// The nodes the drawing fills, made by mountBugButton.
let nodes = null;

function setOpen(open) {
    nodes.root.classList.toggle("bugButton__open", open);
}

// A line of the card: its icon, then its text.
function createLine(iconClass, text) {
    return withChildren(element("div", "bugButton__line"), [element("div", `bugButton__lineIcon ${iconClass}`), text]);
}

// Makes the button at the end of parent; once, before the first drawing.
export function mountBugButton(parent) {
    const bugsText = element("div", "bugButton__text");
    const likeText = element("div", "bugButton__text");
    const openLabel = element("div", "bugButton__openLabel");
    const domain = element("div", "bugButton__domain");
    const link = withChildren(element("div", "bugButton__link"), [
        withChildren(element("div", "bugButton__openText"), [openLabel, domain]),
        element("div", "bugButton__external"),
    ]);
    const card = withChildren(element("div", "bugButton__card"), [
        createLine("bugButton__bug", bugsText),
        createLine("bugButton__like", likeText),
        link,
    ]);
    const trigger = withChildren(element("div", "bugButton__trigger"), [element("div", "bugButton__icon")]);
    const root = withChildren(element("div", "bugButton"), [card, trigger]);
    nodes = { root, bugsText, likeText, openLabel, domain };
    trigger.addEventListener("click", () => setOpen(!root.classList.contains("bugButton__open")));
    link.addEventListener("click", () => {
        setOpen(false);
        window.model.modPage.onOpen();
    });
    document.addEventListener("click", (event) => {
        let node = event.target;
        while (node && node !== root) {
            node = node.parentNode;
        }
        if (!node) {
            setOpen(false);
        }
    }, true);
    document.addEventListener("keydown", (event) => {
        if (event.keyCode === ESCAPE) {
            setOpen(false);
        }
    });
    parent.appendChild(root);
}

// Draws the card's texts from the model; on every change of it.
export function drawBugButton() {
    const model = window.model && window.model.modPage;
    if (!nodes || !model) {
        return;
    }
    nodes.bugsText.textContent = model.bugsText;
    nodes.likeText.textContent = model.likeText;
    nodes.openLabel.textContent = model.openLabel;
    nodes.domain.textContent = model.domain;
}
