// Scroll view: a list (.scrollView__content, its rows in one block) that scrolls in its box (.scrollView) with a bar
// right of it, like the client's barracks list (its VerticalScroll): arrows at the ends, the thumb on a rail, the
// client's images. Gameface draws no bar of its own. The page scrolls the list itself: the wheel and the arrows
// SCROLL_STEP (Gameface's own wheel step is a few pixels), a click on the rail a page, the thumb follows a drag.
// Gameface gives a negative deltaY for the wheel turned towards the user (down). The bar shows only when the list
// does not fit.
// It follows the sizes, as the client's scroll does (useRefResizeObserver): of the visible list (shown, hidden, the
// window resized) and of its rows (filled again); Gameface lays a list out a few frames after it changes.
// Its styles are in ScrollView.css, linked in HitsView.html.
import { element } from "../../common/dom.js";

// The wheel's and the arrows' step in rem, the same in all lists and panels that scroll.
export const SCROLL_STEP = 90;
// A drag of a thumb that ended this long ago in ms is still ending: the click it makes is not a click elsewhere.
const DRAG_CLICK_MS = 300;
let dragEndedAt = 0;

export function isDragEnding() {
    return Date.now() - dragEndedAt < DRAG_CLICK_MS;
}

export class ScrollView {
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
        return viewEnv.remToPx(SCROLL_STEP);
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
