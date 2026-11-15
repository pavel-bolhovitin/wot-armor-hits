// The view model as the page reads it (window.model).

// Array items of a view model may come wrapped as {value: item}.
export function arrayItems(array) {
    const items = [];
    for (let index = 0; array && index < array.length; index++) {
        const item = array[index];
        items.push(item && item.value !== undefined ? item.value : item);
    }
    return items;
}
