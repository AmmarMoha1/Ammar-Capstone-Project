// Wajha interface enhancements. Every page works without JavaScript; these add motion and shortcuts.
document.documentElement.classList.replace("no-js", "js");

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const isRtl = document.documentElement.dir === "rtl";

// Copy-to-clipboard buttons: <button data-copy-target="element-id" data-copied-label="Copied" hidden>.
// Buttons stay hidden when the Clipboard API is unavailable. A button inside a boarding-pass
// stub also "tears" the stub for a moment.
document.querySelectorAll("[data-copy-target]").forEach((button) => {
    if (!navigator.clipboard) return;
    button.hidden = false;
    const label = button.textContent;
    button.addEventListener("click", async () => {
        const text = document.getElementById(button.dataset.copyTarget).textContent.trim();
        const stub = button.closest(".pass__stub");
        try {
            await navigator.clipboard.writeText(text);
            button.textContent = button.dataset.copiedLabel || "Copied";
            button.dataset.copied = "";
            stub?.classList.add("is-torn");
        } catch {
            button.textContent = button.dataset.failedLabel || "Copy failed";
        }
        setTimeout(() => {
            button.textContent = label;
            delete button.dataset.copied;
            stub?.classList.remove("is-torn");
        }, 1800);
    });
});

// Fade cards in as they scroll into view.
const revealItems = document.querySelectorAll("[data-reveal]");
if ("IntersectionObserver" in window && !reduceMotion) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
        });
    }, { threshold: 0.12 });
    revealItems.forEach((item) => observer.observe(item));
} else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
}

// Landing page: a 3D stack of postcards that shuffles itself and on click.
document.querySelectorAll("[data-deck]").forEach((deck) => {
    const cards = [...deck.querySelectorAll(".deck__card")];
    if (cards.length < 2) return;
    deck.classList.add("is-enhanced");
    let top = 0;
    const layout = () => {
        cards.forEach((card, index) => {
            const offset = (index - top + cards.length) % cards.length;
            const x = (isRtl ? -1 : 1) * offset * 34;
            card.style.zIndex = cards.length - offset;
            card.style.filter = `brightness(${1 - offset * 0.05})`;
            card.style.transform = offset === 0
                ? `translate3d(0, 0, 60px) rotateY(${isRtl ? 8 : -8}deg) rotateX(6deg) rotate(${isRtl ? 3 : -3}deg)`
                : `translate3d(${x}px, ${-offset * 16}px, ${-offset * 70}px) rotateY(${isRtl ? 18 : -18}deg) rotateX(8deg) rotate(${(isRtl ? -1 : 1) * offset * 4}deg)`;
            card.setAttribute("aria-hidden", offset === 0 ? "false" : "true");
        });
    };
    const next = () => { top = (top + 1) % cards.length; layout(); };
    layout();
    deck.addEventListener("click", next);
    if (reduceMotion) return;
    let timer = setInterval(next, 2800);
    deck.addEventListener("pointerenter", () => clearInterval(timer));
    deck.addEventListener("pointerleave", () => { timer = setInterval(next, 2800); });
});

// Landing page: "How it works" cards flip on hover, click, Enter or Space.
document.querySelectorAll(".flip__inner").forEach((button) => {
    button.addEventListener("click", () => {
        button.setAttribute("aria-pressed", button.getAttribute("aria-pressed") !== "true");
    });
});

// Trip Room: split-flap board that shuffles airport codes before settling.
document.querySelectorAll("[data-flaps]").forEach((board) => {
    const cells = [...board.querySelectorAll(".flap")];
    const final = cells.map((cell) => cell.textContent);
    if (reduceMotion) return;
    const codes = (board.dataset.flaps || "TBS CAI GYD SJJ IST").split(" ");
    const letters = "ABCDEFGHJKLMNPQRSTUVWXYZ";
    cells.forEach((cell, i) => {
        let step = 0;
        const total = 16 + i * 6;
        const tick = () => {
            cell.classList.remove("is-ticking");
            void cell.offsetWidth;
            cell.classList.add("is-ticking");
            if (step >= total) { cell.textContent = final[i]; return; }
            cell.textContent = step % 6 === 5
                ? (codes[Math.floor(step / 6) % codes.length][i] || final[i])
                : letters[Math.floor(Math.random() * letters.length)];
            step += 1;
            setTimeout(tick, 70);
        };
        tick();
    });
});

// Recommendations: turn the scrollable row of cards into a 3D coverflow with a detail panel.
document.querySelectorAll("[data-coverflow]").forEach((flow) => {
    const stage = flow.querySelector(".coverflow__stage");
    const covers = [...flow.querySelectorAll(".cover")];
    const panels = [...document.querySelectorAll(".rec-panel")];
    const dots = flow.querySelector(".dots");
    const prev = flow.querySelector("[data-prev]");
    const next = flow.querySelector("[data-next]");
    if (covers.length < 2 || !dots) return;

    flow.classList.add("is-enhanced");
    const direction = isRtl ? -1 : 1;
    let current = 0;

    const dotButtons = covers.map((cover, index) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.setAttribute("aria-label", cover.dataset.label);
        dot.addEventListener("click", () => show(index));
        dots.appendChild(dot);
        return dot;
    });

    function show(index) {
        current = Math.max(0, Math.min(covers.length - 1, index));
        covers.forEach((cover, k) => {
            const offset = k - current;
            const distance = Math.abs(offset);
            cover.style.transform =
                `translateX(${offset * 62 * direction}%) translateZ(${-distance * 180}px) rotateY(${-offset * 38 * direction}deg)`;
            cover.style.zIndex = 10 - distance;
            cover.style.opacity = distance > 2 ? 0 : 1;
            cover.style.filter = offset === 0 ? "none" : `saturate(.6) brightness(${1 - distance * 0.08})`;
            cover.classList.toggle("is-center", offset === 0);
            cover.querySelector("a").tabIndex = offset === 0 ? 0 : -1;
        });
        dotButtons.forEach((dot, k) => dot.setAttribute("aria-current", k === current));
        panels.forEach((panel, k) => panel.classList.toggle("is-active", k === current));
        prev.disabled = current === 0;
        next.disabled = current === covers.length - 1;
    }

    covers.forEach((cover, index) => {
        cover.addEventListener("click", (event) => {
            if (index !== current) { event.preventDefault(); show(index); }
        });
    });
    prev.addEventListener("click", () => show(current - 1));
    next.addEventListener("click", () => show(current + 1));
    flow.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") show(current - direction);
        if (event.key === "ArrowRight") show(current + direction);
    });
    let startX = null;
    stage.addEventListener("pointerdown", (event) => { startX = event.clientX; });
    stage.addEventListener("pointerup", (event) => {
        if (startX !== null && Math.abs(event.clientX - startX) > 40) {
            show(current + (event.clientX < startX ? direction : -direction));
        }
        startX = null;
    });
    show(0);
});
