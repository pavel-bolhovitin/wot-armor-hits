// The client's tooltip over a control (a backport tooltip: HitsView.getTooltipData finds it by the arguments, strings
// and numbers), shown and hidden like the client's pages do (a view event, as OpenWG Gameface's libs/views.js sends).
export function clientTooltip(on, args) {
    const event = {
        __Type: "GFViewEventProxy",
        type: 1,
        contentID: window.model.tooltipContentId,
        decoratorID: window.model.tooltipDecoratorId,
        targetID: 0,
        on: on,
    };
    if (on) {
        event.isMouseEvent = true;
        event.arguments = Object.keys(args).map((name) => typeof args[name] === "number"
            ? { __Type: "GFValueProxy", name, number: args[name] }
            : { __Type: "GFValueProxy", name, string: args[name] });
    }
    viewEnv.handleViewEvent(event);
}
