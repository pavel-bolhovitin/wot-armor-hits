// Drop-down menu: the settings' (components/SettingsButton/), the hits filter's (components/HitsPanel/). Its user
// places it and shows it while it is open; a click inside it stays there, a click elsewhere or Escape closes it.
// Its styles are in DropMenu.css, linked in HitsView.html.
import { element, withChildren } from "../../common/dom.js";

const ESCAPE = 27;

// The menu with its children and className, the user's own class (its place, its width); close(), called on a click
// elsewhere or Escape. The control that opens it stops its own click, else that click would close it at once.
export function dropMenu(className, children, close) {
    const menu = withChildren(element("div", `dropMenu ${className}`), children);
    menu.addEventListener("click", (event) => event.stopPropagation());
    document.addEventListener("click", () => close());
    document.addEventListener("keydown", (event) => {
        if (event.keyCode === ESCAPE) {
            close();
        }
    });
    return menu;
}

// A line of the menu: its parts in a row, lighter on hover; className adds the user's own class.
export function dropMenuItem(className, children) {
    return withChildren(element("div", `dropMenu__item ${className}`), children || []);
}
