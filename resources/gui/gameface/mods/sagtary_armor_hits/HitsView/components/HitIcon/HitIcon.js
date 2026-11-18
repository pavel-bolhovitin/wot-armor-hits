// Hit icon, 16 x 16: a hit's result or its critical on the received or the dealt side (the mod's copies of the client's
// damage log icons), a vehicle class (the client's battle atlas).
// Its styles are in HitIcon.css, linked in HitsView.html.
import { element } from "../../common/dom.js";

// The icon of a result (damage, blocked, ricochet, noDamage) or of a critical, on a side (received, dealt).
export function hitIcon(kind, side) {
    return element("div", `hitIcon hitIcon__${kind}__${side}`);
}

// The icon of a vehicle class (light, middle, heavy, destroyer, art); empty without one.
export function classIcon(vehicleClass) {
    return element("div", vehicleClass ? `hitIcon hitIcon__class__${vehicleClass}` : "hitIcon");
}
