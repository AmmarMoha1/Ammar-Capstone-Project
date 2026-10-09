// Copy-to-clipboard buttons: <button data-copy-target="element-id" hidden>.
// Buttons stay hidden when JavaScript or the Clipboard API is unavailable.
document.querySelectorAll("[data-copy-target]").forEach((button) => {
    if (!navigator.clipboard) return;
    button.hidden = false;
    button.addEventListener("click", async () => {
        const text = document.getElementById(button.dataset.copyTarget).textContent.trim();
        const label = button.textContent;
        try {
            await navigator.clipboard.writeText(text);
            button.textContent = "Copied ✓";
        } catch {
            button.textContent = "Copy failed";
        }
        setTimeout(() => { button.textContent = label; }, 2000);
    });
});
