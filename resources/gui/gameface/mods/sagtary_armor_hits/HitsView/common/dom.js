// The page's nodes, made in its scripts with createElement: the markup of a part is in its script, there the moment the
// part is made.

// A node of a tag and a class, with its text when given.
export function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text !== undefined) {
        node.textContent = text;
    }
    return node;
}

// The node with the children put into it in order, so that a part's tree reads as nested calls.
export function withChildren(node, children) {
    children.forEach((child) => node.appendChild(child));
    return node;
}
