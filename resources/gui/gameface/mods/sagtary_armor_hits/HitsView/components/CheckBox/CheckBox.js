// Check box of the drop-down menus (the settings menu's, the hits filter's): a frame; on, the accent's frame and fill
// and its check. The line it is on takes the click.
// Its styles are in CheckBox.css, linked in HitsView.html.
import { element, withChildren } from "../../common/dom.js";

// A check box, on or off; className adds the user's own class (its place in the line).
export function checkBox(isOn, className) {
    const box = withChildren(element("div", className ? `checkBox ${className}` : "checkBox"), [
        element("div", "checkBox__check"),
    ]);
    box.classList.toggle("checkBox__on", Boolean(isOn));
    return box;
}
