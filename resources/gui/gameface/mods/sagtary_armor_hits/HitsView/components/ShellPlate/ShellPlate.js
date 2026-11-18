// Shell plate, the hits list's and the shot panel's: the shell kind on a plate, like in the client's damage log; gold
// for a premium shell, inverted for an SPG's. Without a text the plate keeps its place, unseen.
// Its styles are in ShellPlate.css, linked in HitsView.html.
import { element } from "../../common/dom.js";

// The plate of a shell: its kind's text, premium, an SPG's; className adds the user's own class (its place).
export function shellPlate(text, isGold, isSpg, className) {
    const plate = element("div", className ? `shellPlate ${className}` : "shellPlate", text);
    plate.classList.toggle("shellPlate__none", !text);
    plate.classList.toggle("shellPlate__gold", Boolean(isGold));
    plate.classList.toggle("shellPlate__spg", Boolean(isSpg));
    return plate;
}
